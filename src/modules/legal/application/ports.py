"""Ports owned by the legal module's application layer."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date
from uuid import UUID

from src.modules.legal.application.records import (
    CandidateStatus,
    LegalDocumentMetadata,
    LegalDocumentRecord,
    LegalDocumentStatus,
    RelationCandidateRecord,
)
from src.modules.legal.domain.models import ProvisionVersion
from src.modules.legal.domain.qa import ProvisionHit


class LegalDocumentRepositoryPort(ABC):
    @abstractmethod
    async def acquire_publish_lock(self) -> None:
        """Serialize publishes for the rest of the current transaction."""

    @abstractmethod
    async def delete_document(self, document_id: UUID) -> None:
        """Delete a document and its relation candidates."""

    @abstractmethod
    async def create_document(self, record: LegalDocumentRecord) -> None: ...

    @abstractmethod
    async def save_document(self, record: LegalDocumentRecord) -> None: ...

    @abstractmethod
    async def get_document(self, document_id: UUID) -> LegalDocumentRecord | None: ...

    @abstractmethod
    async def get_document_by_number(self, number: str) -> LegalDocumentRecord | None: ...

    @abstractmethod
    async def get_document_by_sha256(self, sha256: str) -> LegalDocumentRecord | None: ...

    @abstractmethod
    async def list_documents(
        self, status: LegalDocumentStatus | None = None
    ) -> list[LegalDocumentRecord]: ...

    @abstractmethod
    async def replace_candidates(
        self, document_id: UUID, candidates: Sequence[RelationCandidateRecord]
    ) -> None: ...

    @abstractmethod
    async def get_candidate(self, candidate_id: UUID) -> RelationCandidateRecord | None: ...

    @abstractmethod
    async def save_candidate(self, candidate: RelationCandidateRecord) -> None: ...

    @abstractmethod
    async def list_candidates(self, document_id: UUID) -> list[RelationCandidateRecord]: ...

    @abstractmethod
    async def list_candidates_targeting(
        self, target_number: str, statuses: Sequence[CandidateStatus]
    ) -> list[RelationCandidateRecord]: ...


class LegalTextExtractorPort(ABC):
    @abstractmethod
    async def extract_text(self, content: bytes, file_type: str) -> str:
        """Return cleaned text; raise LegalTextExtractionError on failure."""


class LegalSearchIndexPort(ABC):
    @abstractmethod
    async def ensure_collection(self) -> None: ...

    @abstractmethod
    async def replace_provision_versions(
        self,
        provision_key: str,
        document: LegalDocumentMetadata,
        label: str,
        versions: Sequence[ProvisionVersion],
    ) -> None:
        """Upsert the given versions and delete any other point of the provision."""


class LegalProvisionSearchPort(ABC):
    @abstractmethod
    async def search_in_force(
        self,
        vector: Sequence[float],
        day: date,
        limit: int,
        *,
        provision_keys: Sequence[str] | None = None,
        numbers: Sequence[str] | None = None,
        min_score: float | None = None,
    ) -> list[ProvisionHit]:
        """Most similar provision versions in force on `day`, optionally restricted."""

    @abstractmethod
    async def list_versions(self, provision_key: str | None = None) -> list[ProvisionHit]:
        """All indexed versions, or the versions of one provision."""

    @abstractmethod
    async def count_versions(self) -> int: ...


class LegalKeywordSearchPort(ABC):
    @abstractmethod
    async def search(self, query: str, day: date, limit: int) -> list[ProvisionHit]: ...


class LegalRerankerPort(ABC):
    @abstractmethod
    async def rerank(
        self, query: str, hits: Sequence[ProvisionHit], top_k: int
    ) -> list[ProvisionHit]: ...
