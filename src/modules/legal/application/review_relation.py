"""Admin review of relation candidates: approve, reject, or edit."""

from dataclasses import dataclass
from datetime import date
from typing import Literal
from uuid import UUID

from src.modules.legal.application.errors import (
    InvalidLegalDocumentInput,
    InvalidLegalDocumentState,
    RelationCandidateNotFound,
)
from src.modules.legal.application.ports import LegalDocumentRepositoryPort
from src.modules.legal.application.records import (
    CandidateStatus,
    LegalDocumentStatus,
    RelationCandidateRecord,
    utc_now,
)
from src.modules.legal.domain.extraction import DOCUMENT_NUMBER_PATTERN
from src.modules.legal.domain.models import RelationType
from src.modules.legal.domain.provision_key import is_valid_provision_ref

ReviewAction = Literal["approve", "reject", "edit"]


@dataclass(frozen=True)
class ReviewDecision:
    candidate_id: UUID
    action: ReviewAction
    reviewer_id: UUID
    note: str | None = None
    target_number: str | None = None
    target_provision_ref: str | None = None
    effective_date: date | None = None
    new_text: str | None = None


@dataclass(frozen=True)
class ReviewOutcome:
    candidate: RelationCandidateRecord
    republish_document_id: UUID | None


class ReviewRelationCandidate:
    def __init__(self, repository: LegalDocumentRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, decision: ReviewDecision) -> ReviewOutcome:
        candidate = await self._repository.get_candidate(decision.candidate_id)
        if candidate is None:
            raise RelationCandidateNotFound(str(decision.candidate_id))
        was_approved = candidate.status is CandidateStatus.APPROVED

        if decision.action == "edit":
            await self._edit(candidate, decision)
        elif decision.action == "approve":
            await self._approve(candidate)
        else:
            candidate.status = CandidateStatus.REJECTED

        candidate.reviewed_by = decision.reviewer_id
        candidate.reviewed_at = utc_now()
        candidate.review_note = decision.note
        await self._repository.save_candidate(candidate)

        source = await self._repository.get_document(candidate.legal_document_id)
        touches_graph = was_approved or candidate.status is CandidateStatus.APPROVED
        republish = (
            source.id
            if source is not None
            and source.status is LegalDocumentStatus.PUBLISHED
            and touches_graph
            else None
        )
        return ReviewOutcome(candidate=candidate, republish_document_id=republish)

    async def _edit(self, candidate: RelationCandidateRecord, decision: ReviewDecision) -> None:
        if decision.target_number is not None:
            number = decision.target_number.strip()
            if DOCUMENT_NUMBER_PATTERN.fullmatch(number) is None:
                raise InvalidLegalDocumentInput(f"Invalid legal document number: {number}")
            candidate.target_number = number
        if decision.target_provision_ref is not None:
            ref = decision.target_provision_ref.strip()
            if ref and not is_valid_provision_ref(ref):
                raise InvalidLegalDocumentInput(f"Invalid provision reference: {ref}")
            candidate.target_provision_ref = ref or None
        if decision.new_text is not None:
            if not decision.new_text.strip():
                raise InvalidLegalDocumentInput("New text cannot be empty")
            candidate.new_text = decision.new_text.strip()
        if decision.effective_date is not None:
            candidate.effective_date = decision.effective_date

        known = await self._repository.get_document_by_number(candidate.target_number)
        candidate.status = (
            CandidateStatus.PENDING if known is not None else CandidateStatus.UNRESOLVED_TARGET
        )

    async def _approve(self, candidate: RelationCandidateRecord) -> None:
        if await self._repository.get_document_by_number(candidate.target_number) is None:
            raise InvalidLegalDocumentState(
                f"Target document {candidate.target_number} is not in the legal corpus"
            )
        if candidate.type is RelationType.AMENDS and (
            candidate.target_provision_ref is None or not (candidate.new_text or "").strip()
        ):
            raise InvalidLegalDocumentInput("An amendment needs a target provision and new text")
        candidate.status = CandidateStatus.APPROVED
