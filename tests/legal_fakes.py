"""In-memory fakes shared by legal module tests."""

from collections.abc import Sequence
from copy import deepcopy
from datetime import date, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from src.modules.legal.application.errors import LegalTextExtractionError
from src.modules.legal.application.ports import (
    LegalDocumentRepositoryPort,
    LegalKeywordSearchPort,
    LegalProvisionSearchPort,
    LegalSearchIndexPort,
    LegalTextExtractorPort,
)
from src.modules.legal.application.records import (
    CandidateStatus,
    LegalDocumentMetadata,
    LegalDocumentRecord,
    LegalDocumentStatus,
    RelationCandidateRecord,
)
from src.modules.legal.application.serialization import provisions_to_json
from src.modules.legal.domain.models import ProvisionVersion, RelationType
from src.modules.legal.domain.parser import parse_legal_structure
from src.modules.legal.domain.provision_key import describe_provision_ref
from src.modules.legal.domain.qa import ProvisionHit
from src.shared.ports.legal_graph import (
    GraphRelation,
    GraphVersion,
    LegalDocumentNode,
    LegalGraphPort,
    ProvisionContext,
    ProvisionNode,
)
from src.shared.ports.storage import StoragePort

ADMIN_ID = UUID("00000000-0000-0000-0000-00000000a0a0")


class InMemoryLegalRepository(LegalDocumentRepositoryPort):
    def __init__(self) -> None:
        self.documents: dict[UUID, LegalDocumentRecord] = {}
        self.candidates: dict[UUID, RelationCandidateRecord] = {}
        self.events: list[str] = []

    async def acquire_publish_lock(self) -> None:
        self.events.append("acquire_publish_lock")

    async def delete_document(self, document_id: UUID) -> None:
        self.documents.pop(document_id, None)
        self.candidates = {
            key: value
            for key, value in self.candidates.items()
            if value.legal_document_id != document_id
        }

    async def create_document(self, record: LegalDocumentRecord) -> None:
        self.documents[record.id] = deepcopy(record)

    async def save_document(self, record: LegalDocumentRecord) -> None:
        if record.id not in self.documents:
            raise KeyError(record.id)
        self.documents[record.id] = deepcopy(record)

    async def get_document(self, document_id: UUID) -> LegalDocumentRecord | None:
        record = self.documents.get(document_id)
        return deepcopy(record) if record else None

    async def get_document_by_number(self, number: str) -> LegalDocumentRecord | None:
        return next(
            (deepcopy(d) for d in self.documents.values() if d.metadata.number == number), None
        )

    async def get_document_by_sha256(self, sha256: str) -> LegalDocumentRecord | None:
        return next((deepcopy(d) for d in self.documents.values() if d.sha256 == sha256), None)

    async def list_documents(
        self, status: LegalDocumentStatus | None = None
    ) -> list[LegalDocumentRecord]:
        return [
            deepcopy(d) for d in self.documents.values() if status is None or d.status is status
        ]

    async def replace_candidates(
        self, document_id: UUID, candidates: Sequence[RelationCandidateRecord]
    ) -> None:
        self.candidates = {
            key: value
            for key, value in self.candidates.items()
            if value.legal_document_id != document_id
        }
        for candidate in candidates:
            self.candidates[candidate.id] = deepcopy(candidate)

    async def get_candidate(self, candidate_id: UUID) -> RelationCandidateRecord | None:
        candidate = self.candidates.get(candidate_id)
        return deepcopy(candidate) if candidate else None

    async def save_candidate(self, candidate: RelationCandidateRecord) -> None:
        self.candidates[candidate.id] = deepcopy(candidate)

    async def list_candidates(self, document_id: UUID) -> list[RelationCandidateRecord]:
        self.events.append("list_candidates")
        return [deepcopy(c) for c in self.candidates.values() if c.legal_document_id == document_id]

    async def list_candidates_targeting(
        self, target_number: str, statuses: Sequence[CandidateStatus]
    ) -> list[RelationCandidateRecord]:
        return [
            deepcopy(c)
            for c in self.candidates.values()
            if c.target_number == target_number and c.status in statuses
        ]


class FakeStorage(StoragePort):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        self.objects[key] = data
        return key

    async def download(self, key: str) -> bytes:
        if key not in self.objects:
            raise FileNotFoundError(key)
        return self.objects[key]

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self.objects


class FakeTextExtractor(LegalTextExtractorPort):
    """Decodes UTF-8 bytes; empty content fails like a real extractor."""

    async def extract_text(self, content: bytes, file_type: str) -> str:
        text = content.decode("utf-8").strip()
        if not text:
            raise LegalTextExtractionError("No text extracted")
        return text


def make_document(
    number: str,
    *,
    status: LegalDocumentStatus = LegalDocumentStatus.PUBLISHED,
    effective_date: date = date(2024, 8, 1),
    text: str | None = None,
    doc_type: str = "law",
) -> LegalDocumentRecord:
    parsed = provisions_to_json(parse_legal_structure(text, number).provisions) if text else None
    return LegalDocumentRecord(
        id=uuid4(),
        metadata=LegalDocumentMetadata(
            number=number,
            doc_type=doc_type,
            title=f"Văn bản {number}",
            issuer="Quốc hội",
            issued_date=effective_date - timedelta(days=30),
            effective_date=effective_date,
        ),
        file_key=f"legal/{number.replace('/', '-')}.txt",
        file_type="txt",
        sha256=sha256(number.encode()).hexdigest(),
        status=status,
        uploaded_by=ADMIN_ID,
        parsed_structure=parsed,
        published_at=(
            datetime(2024, 7, 31, 9, 0) if status is LegalDocumentStatus.PUBLISHED else None
        ),
    )


def make_candidate(
    source: LegalDocumentRecord,
    relation_type: RelationType,
    target_number: str,
    *,
    ref: str | None = None,
    new_text: str | None = None,
    source_key: str | None = None,
    status: CandidateStatus = CandidateStatus.APPROVED,
    effective_date: date | None = None,
) -> RelationCandidateRecord:
    return RelationCandidateRecord(
        id=uuid4(),
        legal_document_id=source.id,
        type=relation_type,
        target_number=target_number,
        evidence_text="bằng chứng",
        confidence=0.9,
        extractor="rule",
        status=status,
        effective_date=effective_date or source.metadata.effective_date,
        source_provision_key=source_key,
        target_provision_ref=ref,
        new_text=new_text,
    )


class FakeLLM:
    """LLMPort stand-in returning queued responses; an Exception instance is raised."""

    def __init__(self, *responses: str | Exception, stream_chunks: Sequence[str] = ()) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict[str, str]]] = []
        self.stream_chunks = list(stream_chunks) or ["Áp dụng tại ngày ", "... [1]."]
        self.stream_calls: list[list[dict[str, str]]] = []

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: object,
    ) -> str:
        self.calls.append(messages)
        response = self.responses.pop(0) if self.responses else '{"amendments": []}'
        if isinstance(response, Exception):
            raise response
        return response

    async def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: object,
    ):
        self.stream_calls.append(messages)
        for chunk in self.stream_chunks:
            yield chunk


class FakeLegalGraph(LegalGraphPort):
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.documents: dict[str, LegalDocumentNode] = {}
        self.provisions: dict[str, ProvisionNode] = {}
        self.timelines: dict[str, list[GraphVersion]] = {}
        self.relations: dict[str, list[GraphRelation]] = {}
        self.deleted_provisions: list[str] = []
        self.fail_on: str | None = None
        self.contexts: dict[str, ProvisionContext] = {}
        self.guides: list[str] = []
        self.fail_reads = False

    def _record(self, call: str) -> None:
        self.calls.append(call)
        if call == self.fail_on:
            raise ConnectionError(f"{call} failed")

    async def ensure_schema(self) -> None:
        self._record("ensure_schema")

    async def upsert_document(self, document: LegalDocumentNode) -> None:
        self._record("upsert_document")
        self.documents[document.number] = document

    async def upsert_provisions(self, provisions) -> None:
        self._record("upsert_provisions")
        for provision in provisions:
            self.provisions[provision.provision_key] = provision

    async def replace_provision_timeline(self, provision_key: str, versions) -> None:
        self._record("replace_provision_timeline")
        self.timelines[provision_key] = list(versions)

    async def replace_document_relations(self, source_document: str, relations) -> None:
        self._record("replace_document_relations")
        self.relations[source_document] = list(relations)

    async def delete_provisions(self, provision_keys) -> None:
        self._record("delete_provisions")
        for key in provision_keys:
            self.deleted_provisions.append(key)
            self.provisions.pop(key, None)
            self.timelines.pop(key, None)

    async def expand_context(self, provision_keys, day) -> dict[str, ProvisionContext]:
        if self.fail_reads:
            raise ConnectionError("neo4j unavailable")
        return {key: self.contexts[key] for key in provision_keys if key in self.contexts}

    async def guiding_documents(self, provision_keys) -> list[str]:
        if self.fail_reads:
            raise ConnectionError("neo4j unavailable")
        return list(self.guides)

    async def health_check(self) -> bool:
        return True

    async def close(self) -> None:
        self.calls.append("close")


class FakeSearchIndex(LegalSearchIndexPort):
    def __init__(self) -> None:
        self.ensured = 0
        self.versions: dict[str, list[ProvisionVersion]] = {}
        self.labels: dict[str, str] = {}

    async def ensure_collection(self) -> None:
        self.ensured += 1

    async def replace_provision_versions(self, provision_key, document, label, versions) -> None:
        self.versions[provision_key] = list(versions)
        self.labels[provision_key] = label


def make_hit(
    key: str,
    text: str,
    valid_from: date,
    valid_to: date | None = None,
    *,
    number: str | None = None,
    title: str = "Luật Đất đai",
    label: str | None = None,
    doc_type: str = "law",
    version_id: str | None = None,
) -> ProvisionHit:
    document_number, ref = key.split("#", 1)
    return ProvisionHit(
        version_id=version_id or f"{key}@{valid_from.isoformat()}",
        provision_key=key,
        number=number or document_number,
        doc_type=doc_type,
        title=title,
        label=label or describe_provision_ref(ref)[1],
        text=text,
        page=None,
        valid_from=valid_from,
        valid_to=valid_to,
        score=0.5,
    )


class FakeProvisionSearch(LegalProvisionSearchPort):
    def __init__(self, hits: Sequence[ProvisionHit] = ()) -> None:
        self.hits = list(hits)
        self.calls: list[dict[str, object]] = []

    async def search_in_force(
        self, vector, day, limit, *, provision_keys=None, numbers=None, min_score=None
    ) -> list[ProvisionHit]:
        self.calls.append(
            {
                "day": day,
                "limit": limit,
                "provision_keys": provision_keys,
                "numbers": numbers,
                "min_score": min_score,
            }
        )
        found = [
            hit
            for hit in self.hits
            if hit.in_force_on(day)
            and (provision_keys is None or hit.provision_key in provision_keys)
            and (numbers is None or hit.number in numbers)
            and (min_score is None or hit.score >= min_score)
        ]
        return found[:limit]

    async def list_versions(self, provision_key: str | None = None) -> list[ProvisionHit]:
        return [h for h in self.hits if provision_key is None or h.provision_key == provision_key]

    async def count_versions(self) -> int:
        return len(self.hits)


class FakeKeywordSearch(LegalKeywordSearchPort):
    def __init__(self, hits: Sequence[ProvisionHit] = (), fail: bool = False) -> None:
        self.hits = list(hits)
        self.fail = fail

    async def search(self, query: str, day: date, limit: int) -> list[ProvisionHit]:
        if self.fail:
            raise RuntimeError("bm25 unavailable")
        return [hit for hit in self.hits if hit.in_force_on(day)][:limit]
