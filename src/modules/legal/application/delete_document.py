"""Delete a legal document that has never been published."""

import logging
from uuid import UUID

from src.modules.legal.application.errors import InvalidLegalDocumentState, LegalDocumentNotFound
from src.modules.legal.application.ports import LegalDocumentRepositoryPort
from src.modules.legal.application.records import CandidateStatus, LegalDocumentStatus
from src.shared.ports.storage import StoragePort

logger = logging.getLogger(__name__)

_BUSY_STATUSES = frozenset({LegalDocumentStatus.PARSING, LegalDocumentStatus.PUBLISHING})


class DeleteLegalDocument:
    def __init__(self, repository: LegalDocumentRepositoryPort, storage: StoragePort) -> None:
        self._repository = repository
        self._storage = storage

    async def execute(self, document_id: UUID) -> None:
        document = await self._repository.get_document(document_id)
        if document is None:
            raise LegalDocumentNotFound(str(document_id))
        if document.published_at is not None or document.status in _BUSY_STATUSES:
            raise InvalidLegalDocumentState(
                f"Document {document.metadata.number} has been published or is being processed"
            )

        # Relations of other documents pointing here lose their target again.
        dependents = await self._repository.list_candidates_targeting(
            document.metadata.number, [CandidateStatus.PENDING, CandidateStatus.APPROVED]
        )
        for candidate in dependents:
            if candidate.legal_document_id != document.id:
                candidate.status = CandidateStatus.UNRESOLVED_TARGET
                await self._repository.save_candidate(candidate)

        await self._repository.delete_document(document.id)
        try:
            await self._storage.delete(document.file_key)
        except Exception as exc:  # the row is gone; an orphaned object is only wasted space
            logger.warning("Could not delete stored file %s: %s", document.file_key, exc)
