"""Read-side queries for the legal admin screens."""

from uuid import UUID

from kira.legal.errors import InvalidLegalDocumentStateError, LegalDocumentNotFoundError
from kira.legal.ports import LegalDocumentRepositoryPort
from kira.legal.records import (
    LegalDocumentRecord,
    LegalDocumentStatus,
    RelationCandidateRecord,
)
from kira.legal.services.process_document import PROCESSABLE_STATUSES
from kira.legal.services.publish_document import ensure_publishable


class LegalDocumentQueries:
    def __init__(self, repository: LegalDocumentRepositoryPort) -> None:
        self._repository = repository

    async def list_documents(
        self, status: LegalDocumentStatus | None = None
    ) -> list[LegalDocumentRecord]:
        return await self._repository.list_documents(status)

    async def get_document(self, document_id: UUID) -> LegalDocumentRecord:
        document = await self._repository.get_document(document_id)
        if document is None:
            raise LegalDocumentNotFoundError(str(document_id))
        return document

    async def list_candidates(self, document_id: UUID) -> list[RelationCandidateRecord]:
        await self.get_document(document_id)
        return await self._repository.list_candidates(document_id)

    async def require_publishable(self, document_id: UUID) -> LegalDocumentRecord:
        document = await self.get_document(document_id)
        ensure_publishable(document)
        return document

    async def require_processable(self, document_id: UUID) -> LegalDocumentRecord:
        document = await self.get_document(document_id)
        if document.status not in PROCESSABLE_STATUSES:
            raise InvalidLegalDocumentStateError(
                f"Document {document.metadata.number} cannot be reprocessed in status "
                f"{document.status}"
            )
        return document
