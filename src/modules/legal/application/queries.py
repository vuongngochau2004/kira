"""Read-side queries for the legal admin screens."""

from uuid import UUID

from src.modules.legal.application.errors import InvalidLegalDocumentState, LegalDocumentNotFound
from src.modules.legal.application.ports import LegalDocumentRepositoryPort
from src.modules.legal.application.process_document import PROCESSABLE_STATUSES
from src.modules.legal.application.publish_document import ensure_publishable
from src.modules.legal.application.records import (
    LegalDocumentRecord,
    LegalDocumentStatus,
    RelationCandidateRecord,
)


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
            raise LegalDocumentNotFound(str(document_id))
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
            raise InvalidLegalDocumentState(
                f"Document {document.metadata.number} cannot be reprocessed in status "
                f"{document.status}"
            )
        return document
