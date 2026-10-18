"""Request and response schemas for the legal admin API."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from src.modules.legal.application.provision_history import ProvisionHistory
from src.modules.legal.application.records import LegalDocumentRecord, RelationCandidateRecord
from src.modules.legal.domain.qa import ProvisionHit


class LegalDocumentResponse(BaseModel):
    id: UUID
    number: str
    doc_type: str
    title: str
    issuer: str
    issued_date: date
    effective_date: date
    source_url: str | None
    status: str
    warnings: list[str]
    error_detail: str | None
    provision_count: int
    published_at: datetime | None
    created_at: datetime | None

    @classmethod
    def from_record(cls, record: LegalDocumentRecord) -> "LegalDocumentResponse":
        metadata = record.metadata
        return cls(
            id=record.id,
            number=metadata.number,
            doc_type=metadata.doc_type,
            title=metadata.title,
            issuer=metadata.issuer,
            issued_date=metadata.issued_date,
            effective_date=metadata.effective_date,
            source_url=metadata.source_url,
            status=record.status.value,
            warnings=record.warnings,
            error_detail=record.error_detail,
            provision_count=len(record.parsed_structure or []),
            published_at=record.published_at,
            created_at=record.created_at,
        )


class RelationCandidateResponse(BaseModel):
    id: UUID
    legal_document_id: UUID
    type: str
    source_provision_key: str | None
    target_number: str
    target_provision_ref: str | None
    effective_date: date
    new_text: str | None
    evidence_text: str
    evidence_page: int | None
    extractor: str
    confidence: float
    status: str
    flags: list[str]
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    review_note: str | None

    @classmethod
    def from_record(cls, record: RelationCandidateRecord) -> "RelationCandidateResponse":
        return cls(
            id=record.id,
            legal_document_id=record.legal_document_id,
            type=record.type.value,
            source_provision_key=record.source_provision_key,
            target_number=record.target_number,
            target_provision_ref=record.target_provision_ref,
            effective_date=record.effective_date,
            new_text=record.new_text,
            evidence_text=record.evidence_text,
            evidence_page=record.evidence_page,
            extractor=record.extractor,
            confidence=record.confidence,
            status=record.status.value,
            flags=record.flags,
            reviewed_by=record.reviewed_by,
            reviewed_at=record.reviewed_at,
            review_note=record.review_note,
        )


class CandidateReviewRequest(BaseModel):
    action: Literal["approve", "reject", "edit"]
    note: str | None = None
    target_number: str | None = None
    target_provision_ref: str | None = None
    effective_date: date | None = None
    new_text: str | None = None


class ReviewResponse(BaseModel):
    candidate: RelationCandidateResponse
    republish_task_id: str | None


class TaskResponse(BaseModel):
    document_id: UUID
    task_id: str


class ProvisionVersionResponse(BaseModel):
    version_id: str
    text: str
    page: int | None
    valid_from: date
    valid_to: date | None

    @classmethod
    def from_hit(cls, hit: ProvisionHit) -> "ProvisionVersionResponse":
        return cls(
            version_id=hit.version_id,
            text=hit.text,
            page=hit.page,
            valid_from=hit.valid_from,
            valid_to=hit.valid_to,
        )


class ProvisionHistoryResponse(BaseModel):
    provision_key: str
    label: str
    number: str
    title: str
    doc_type: str
    versions: list[ProvisionVersionResponse]
    in_force: ProvisionVersionResponse | None

    @classmethod
    def from_history(cls, history: ProvisionHistory) -> "ProvisionHistoryResponse":
        return cls(
            provision_key=history.provision_key,
            label=history.label,
            number=history.number,
            title=history.title,
            doc_type=history.doc_type,
            versions=[ProvisionVersionResponse.from_hit(v) for v in history.versions],
            in_force=(
                ProvisionVersionResponse.from_hit(history.in_force) if history.in_force else None
            ),
        )
