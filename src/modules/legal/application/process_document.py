"""Parse an uploaded legal document and propose relation candidates."""

import logging
from collections.abc import Collection
from uuid import UUID, uuid4

from src.modules.legal.application.errors import (
    InvalidLegalDocumentState,
    LegalDocumentNotFound,
    LegalTextExtractionError,
)
from src.modules.legal.application.ports import (
    LegalDocumentRepositoryPort,
    LegalTextExtractorPort,
)
from src.modules.legal.application.records import (
    AUTO_APPROVED_NOTE,
    LLM_EXTRACTION_INCOMPLETE_FLAG,
    CandidateStatus,
    LegalDocumentRecord,
    LegalDocumentStatus,
    RelationCandidateRecord,
    utc_now,
)
from src.modules.legal.application.serialization import provisions_to_json
from src.modules.legal.domain.errors import LegalParseError
from src.modules.legal.domain.extraction import extract_rule_candidates
from src.modules.legal.domain.extraction.llm import (
    build_amendment_messages,
    parse_amendment_response,
    select_amendment_provisions,
)
from src.modules.legal.domain.models import ParseResult, RelationDraft, RelationType
from src.modules.legal.domain.parser import parse_legal_structure
from src.shared.ports.llm import LLMPort
from src.shared.ports.storage import StoragePort
from src.shared.utils.agent import parse_json_response

logger = logging.getLogger(__name__)

PROCESSABLE_STATUSES = frozenset({LegalDocumentStatus.UPLOADED, LegalDocumentStatus.FAILED})
REVIEW_REQUIRED_TYPES = frozenset(
    {RelationType.AMENDS, RelationType.REPEALS, RelationType.REPLACES}
)
LLM_ATTEMPTS = 2


class ProcessLegalDocument:
    def __init__(
        self,
        repository: LegalDocumentRepositoryPort,
        storage: StoragePort,
        extractor: LegalTextExtractorPort,
        llm: LLMPort,
        auto_approve_types: Collection[str],
        llm_max_provisions: int,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._extractor = extractor
        self._llm = llm
        self._auto_approve = (
            frozenset(RelationType(value) for value in auto_approve_types) - REVIEW_REQUIRED_TYPES
        )
        self._llm_max_provisions = llm_max_provisions

    async def execute(self, document_id: UUID) -> LegalDocumentRecord:
        document = await self._repository.get_document(document_id)
        if document is None:
            raise LegalDocumentNotFound(str(document_id))
        if document.status not in PROCESSABLE_STATUSES:
            raise InvalidLegalDocumentState(
                f"Cannot process a document in status {document.status}"
            )

        document.status = LegalDocumentStatus.PARSING
        document.error_detail = None
        await self._repository.save_document(document)

        number = document.metadata.number
        try:
            content = await self._storage.download(document.file_key)
            text = await self._extractor.extract_text(content, document.file_type)
            result = parse_legal_structure(text, number)
        except (FileNotFoundError, LegalTextExtractionError, LegalParseError) as exc:
            logger.warning("Legal document %s could not be parsed: %s", document_id, exc)
            document.status = LegalDocumentStatus.FAILED
            document.error_detail = str(exc)[:1000]
            await self._repository.save_document(document)
            return document

        drafts = extract_rule_candidates(result, number)
        warnings = list(result.warnings)
        llm_drafts, llm_complete = await self._extract_with_llm(result, number, drafts)
        if not llm_complete:
            warnings.append(LLM_EXTRACTION_INCOMPLETE_FLAG)

        candidates = [await self._to_candidate(document, draft) for draft in [*drafts, *llm_drafts]]
        await self._repository.replace_candidates(document.id, candidates)
        await self._resolve_waiting_candidates(number)

        document.parsed_structure = provisions_to_json(result.provisions)
        document.warnings = warnings
        document.status = LegalDocumentStatus.IN_REVIEW
        await self._repository.save_document(document)
        return document

    async def _extract_with_llm(
        self, result: ParseResult, number: str, drafts: list[RelationDraft]
    ) -> tuple[list[RelationDraft], bool]:
        covered = {
            draft.source_provision_key
            for draft in drafts
            if draft.type is RelationType.AMENDS and draft.source_provision_key
        }
        provisions = select_amendment_provisions(result, covered, self._llm_max_provisions)
        if not provisions:
            return [], True
        messages = build_amendment_messages(result, provisions, number)
        for attempt in range(1, LLM_ATTEMPTS + 1):
            try:
                response = await self._llm.generate(messages, temperature=0.0, max_tokens=4000)
                payload = parse_json_response(response)
                return parse_amendment_response(payload, provisions, number), True
            except Exception as exc:  # LLM failures must not block rule-based candidates
                logger.warning(
                    "LLM amendment extraction for %s failed (attempt %d/%d): %s",
                    number,
                    attempt,
                    LLM_ATTEMPTS,
                    exc,
                )
        return [], False

    async def _to_candidate(
        self, document: LegalDocumentRecord, draft: RelationDraft
    ) -> RelationCandidateRecord:
        candidate = RelationCandidateRecord(
            id=uuid4(),
            legal_document_id=document.id,
            type=draft.type,
            target_number=draft.target_number,
            evidence_text=draft.evidence_text,
            confidence=draft.confidence,
            extractor=draft.extractor,
            status=CandidateStatus.PENDING,
            effective_date=document.metadata.effective_date,
            source_provision_key=draft.source_provision_key,
            target_provision_ref=draft.target_provision_ref,
            new_text=draft.new_text,
            evidence_page=draft.evidence_page,
        )
        await self._assign_initial_status(candidate)
        return candidate

    async def _assign_initial_status(self, candidate: RelationCandidateRecord) -> None:
        if await self._repository.get_document_by_number(candidate.target_number) is None:
            candidate.status = CandidateStatus.UNRESOLVED_TARGET
        elif candidate.type in self._auto_approve and candidate.target_provision_ref is None:
            candidate.status = CandidateStatus.APPROVED
            candidate.reviewed_at = utc_now()
            candidate.review_note = AUTO_APPROVED_NOTE
        else:
            candidate.status = CandidateStatus.PENDING

    async def _resolve_waiting_candidates(self, number: str) -> None:
        waiting = await self._repository.list_candidates_targeting(
            number, [CandidateStatus.UNRESOLVED_TARGET]
        )
        for candidate in waiting:
            await self._assign_initial_status(candidate)
            await self._repository.save_candidate(candidate)
