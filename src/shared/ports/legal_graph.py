"""Port for the legal knowledge graph (documents, provisions, versions, relations)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class LegalDocumentNode:
    doc_id: str
    number: str
    doc_type: str
    title: str
    issuer: str
    issued_date: date
    effective_date: date
    source_url: str | None
    file_key: str
    sha256: str


@dataclass(frozen=True)
class ProvisionNode:
    provision_key: str
    document_number: str
    level: str
    label: str
    heading: str
    chapter_label: str | None
    parent_key: str | None


@dataclass(frozen=True)
class GraphVersion:
    version_id: str
    text: str
    text_hash: str
    valid_from: date
    valid_to: date | None
    page: int | None
    introduced_by: str | None


@dataclass(frozen=True)
class GraphRelation:
    """A reviewed legal relation; a None key means the document itself."""

    type: str
    source_document: str
    source_key: str | None
    target_number: str
    target_key: str | None
    effective_date: date
    evidence_text: str
    evidence_page: int | None
    review_id: str
    approved_by: str | None
    approved_at: datetime | None


@dataclass(frozen=True)
class ProvisionContext:
    """Graph facts about a provision as of one date."""

    provision_key: str
    parent_label: str | None
    parent_text: str | None
    introduced_by: str | None
    introduced_by_number: str | None
    introduced_by_title: str | None
    amended_after: date | None


class LegalGraphPort(ABC):
    @abstractmethod
    async def ensure_schema(self) -> None:
        """Create constraints and indexes if missing."""

    @abstractmethod
    async def upsert_document(self, document: LegalDocumentNode) -> None: ...

    @abstractmethod
    async def upsert_provisions(self, provisions: Sequence[ProvisionNode]) -> None:
        """Upsert provisions and link them to their parent provision or document."""

    @abstractmethod
    async def replace_provision_timeline(
        self, provision_key: str, versions: Sequence[GraphVersion]
    ) -> None:
        """Make `versions` the complete version chain of the provision."""

    @abstractmethod
    async def replace_document_relations(
        self, source_document: str, relations: Sequence[GraphRelation]
    ) -> None:
        """Make `relations` the complete set of relations stated by the source document."""

    @abstractmethod
    async def delete_provisions(self, provision_keys: Sequence[str]) -> None:
        """Remove provisions (and their versions) that no longer exist."""

    @abstractmethod
    async def expand_context(
        self, provision_keys: Sequence[str], day: date
    ) -> dict[str, ProvisionContext]:
        """Parent text, amendment provenance and the next change date, as of `day`."""

    @abstractmethod
    async def guiding_documents(self, provision_keys: Sequence[str]) -> list[str]:
        """Numbers of documents that guide these provisions or their documents."""

    @abstractmethod
    async def health_check(self) -> bool: ...

    @abstractmethod
    async def close(self) -> None: ...
