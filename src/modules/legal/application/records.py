"""Application records for legal documents and relation candidates."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from src.modules.legal.domain.models import RelationType

LLM_EXTRACTION_INCOMPLETE_FLAG = "llm_extraction_incomplete"
AUTO_APPROVED_NOTE = "auto-approved: exact document number match"


class LegalDocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    IN_REVIEW = "in_review"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class CandidateStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    UNRESOLVED_TARGET = "unresolved_target"


def utc_now() -> datetime:
    """Naive UTC timestamp, matching the TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class LegalDocumentMetadata:
    number: str
    doc_type: str
    title: str
    issuer: str
    issued_date: date
    effective_date: date
    source_url: str | None = None


@dataclass
class LegalDocumentRecord:
    id: UUID
    metadata: LegalDocumentMetadata
    file_key: str
    file_type: str
    sha256: str
    status: LegalDocumentStatus
    uploaded_by: UUID
    parsed_structure: list[dict[str, Any]] | None = None
    warnings: list[str] = field(default_factory=list)
    error_detail: str | None = None
    published_at: datetime | None = None
    published_keys: list[str] = field(default_factory=list)
    created_at: datetime | None = None


@dataclass
class RelationCandidateRecord:
    id: UUID
    legal_document_id: UUID
    type: RelationType
    target_number: str
    evidence_text: str
    confidence: float
    extractor: str
    status: CandidateStatus
    effective_date: date
    source_provision_key: str | None = None
    target_provision_ref: str | None = None
    new_text: str | None = None
    evidence_page: int | None = None
    flags: list[str] = field(default_factory=list)
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None

    @property
    def target_provision_key(self) -> str | None:
        if self.target_provision_ref is None:
            return None
        return f"{self.target_number}#{self.target_provision_ref}"
