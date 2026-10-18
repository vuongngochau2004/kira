"""SQLAlchemy repository for legal documents and relation candidates."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.legal.application.errors import LegalDocumentNotFound
from src.modules.legal.application.ports import LegalDocumentRepositoryPort
from src.modules.legal.application.records import (
    CandidateStatus,
    LegalDocumentMetadata,
    LegalDocumentRecord,
    LegalDocumentStatus,
    RelationCandidateRecord,
)
from src.modules.legal.domain.models import RelationType
from src.shared.infrastructure.persistence.database.models import (
    LegalDocument,
    LegalRelationCandidate,
)

# Arbitrary application-wide id for pg_advisory_xact_lock that serializes legal publishes.
LEGAL_PUBLISH_LOCK_KEY = 7_340_021_001


def document_to_model(record: LegalDocumentRecord) -> LegalDocument:
    model = LegalDocument(id=record.id, uploaded_by=record.uploaded_by, sha256=record.sha256)
    apply_document(model, record)
    return model


def apply_document(model: LegalDocument, record: LegalDocumentRecord) -> None:
    metadata = record.metadata
    model.number = metadata.number
    model.doc_type = metadata.doc_type
    model.title = metadata.title
    model.issuer = metadata.issuer
    model.issued_date = metadata.issued_date
    model.effective_date = metadata.effective_date
    model.source_url = metadata.source_url
    model.file_key = record.file_key
    model.file_type = record.file_type
    model.status = record.status.value
    model.parsed_structure = record.parsed_structure
    model.warnings = list(record.warnings)
    model.error_detail = record.error_detail
    model.published_at = record.published_at
    model.published_keys = list(record.published_keys)


def document_from_model(model: LegalDocument) -> LegalDocumentRecord:
    return LegalDocumentRecord(
        id=model.id,
        metadata=LegalDocumentMetadata(
            number=model.number,
            doc_type=model.doc_type,
            title=model.title,
            issuer=model.issuer,
            issued_date=model.issued_date,
            effective_date=model.effective_date,
            source_url=model.source_url,
        ),
        file_key=model.file_key,
        file_type=model.file_type,
        sha256=model.sha256,
        status=LegalDocumentStatus(model.status),
        uploaded_by=model.uploaded_by,
        parsed_structure=model.parsed_structure,
        warnings=list(model.warnings or []),
        error_detail=model.error_detail,
        published_at=model.published_at,
        published_keys=list(model.published_keys or []),
        created_at=model.created_at,
    )


def candidate_to_model(record: RelationCandidateRecord) -> LegalRelationCandidate:
    model = LegalRelationCandidate(id=record.id, legal_document_id=record.legal_document_id)
    apply_candidate(model, record)
    return model


def apply_candidate(model: LegalRelationCandidate, record: RelationCandidateRecord) -> None:
    model.type = record.type.value
    model.source_provision_key = record.source_provision_key
    model.target_number = record.target_number
    model.target_provision_ref = record.target_provision_ref
    model.effective_date = record.effective_date
    model.new_text = record.new_text
    model.evidence_text = record.evidence_text
    model.evidence_page = record.evidence_page
    model.extractor = record.extractor
    model.confidence = record.confidence
    model.status = record.status.value
    model.flags = list(record.flags)
    model.reviewed_by = record.reviewed_by
    model.reviewed_at = record.reviewed_at
    model.review_note = record.review_note


def candidate_from_model(model: LegalRelationCandidate) -> RelationCandidateRecord:
    return RelationCandidateRecord(
        id=model.id,
        legal_document_id=model.legal_document_id,
        type=RelationType(model.type),
        target_number=model.target_number,
        evidence_text=model.evidence_text,
        confidence=model.confidence,
        extractor=model.extractor,
        status=CandidateStatus(model.status),
        effective_date=model.effective_date,
        source_provision_key=model.source_provision_key,
        target_provision_ref=model.target_provision_ref,
        new_text=model.new_text,
        evidence_page=model.evidence_page,
        flags=list(model.flags or []),
        reviewed_by=model.reviewed_by,
        reviewed_at=model.reviewed_at,
        review_note=model.review_note,
    )


class SqlAlchemyLegalRepository(LegalDocumentRepositoryPort):
    """Flushes changes; the session owner (request or worker task) commits."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def acquire_publish_lock(self) -> None:
        await self._db.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": LEGAL_PUBLISH_LOCK_KEY}
        )

    async def delete_document(self, document_id: UUID) -> None:
        # legal_relation_candidates rows go with it (ON DELETE CASCADE).
        await self._db.execute(delete(LegalDocument).where(LegalDocument.id == document_id))
        await self._db.flush()

    async def create_document(self, record: LegalDocumentRecord) -> None:
        self._db.add(document_to_model(record))
        await self._db.flush()

    async def save_document(self, record: LegalDocumentRecord) -> None:
        model = await self._db.get(LegalDocument, record.id)
        if model is None:
            raise LegalDocumentNotFound(str(record.id))
        apply_document(model, record)
        await self._db.flush()

    async def get_document(self, document_id: UUID) -> LegalDocumentRecord | None:
        model = await self._db.get(LegalDocument, document_id)
        return document_from_model(model) if model is not None else None

    async def get_document_by_number(self, number: str) -> LegalDocumentRecord | None:
        result = await self._db.execute(select(LegalDocument).where(LegalDocument.number == number))
        model = result.scalar_one_or_none()
        return document_from_model(model) if model is not None else None

    async def get_document_by_sha256(self, sha256: str) -> LegalDocumentRecord | None:
        result = await self._db.execute(select(LegalDocument).where(LegalDocument.sha256 == sha256))
        model = result.scalar_one_or_none()
        return document_from_model(model) if model is not None else None

    async def list_documents(
        self, status: LegalDocumentStatus | None = None
    ) -> list[LegalDocumentRecord]:
        query = select(LegalDocument).order_by(LegalDocument.created_at.desc())
        if status is not None:
            query = query.where(LegalDocument.status == status.value)
        result = await self._db.execute(query)
        return [document_from_model(model) for model in result.scalars()]

    async def replace_candidates(
        self, document_id: UUID, candidates: Sequence[RelationCandidateRecord]
    ) -> None:
        await self._db.execute(
            delete(LegalRelationCandidate).where(
                LegalRelationCandidate.legal_document_id == document_id
            )
        )
        self._db.add_all([candidate_to_model(candidate) for candidate in candidates])
        await self._db.flush()

    async def get_candidate(self, candidate_id: UUID) -> RelationCandidateRecord | None:
        model = await self._db.get(LegalRelationCandidate, candidate_id)
        return candidate_from_model(model) if model is not None else None

    async def save_candidate(self, candidate: RelationCandidateRecord) -> None:
        model = await self._db.get(LegalRelationCandidate, candidate.id)
        if model is None:
            self._db.add(candidate_to_model(candidate))
        else:
            apply_candidate(model, candidate)
        await self._db.flush()

    async def list_candidates(self, document_id: UUID) -> list[RelationCandidateRecord]:
        result = await self._db.execute(
            select(LegalRelationCandidate)
            .where(LegalRelationCandidate.legal_document_id == document_id)
            .order_by(
                LegalRelationCandidate.source_provision_key.nulls_first(),
                LegalRelationCandidate.type,
                LegalRelationCandidate.target_number,
            )
        )
        return [candidate_from_model(model) for model in result.scalars()]

    async def list_candidates_targeting(
        self, target_number: str, statuses: Sequence[CandidateStatus]
    ) -> list[RelationCandidateRecord]:
        result = await self._db.execute(
            select(LegalRelationCandidate).where(
                LegalRelationCandidate.target_number == target_number,
                LegalRelationCandidate.status.in_([status.value for status in statuses]),
            )
        )
        return [candidate_from_model(model) for model in result.scalars()]
