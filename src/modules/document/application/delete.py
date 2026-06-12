"""Document deletion application service."""

import logging
import uuid

from src.modules.document.application.dto import DeleteDocumentRequest, DocumentDeleteResult
from src.shared.ports.document_repository import DocumentRepositoryPort
from src.shared.ports.keyword_index import KeywordIndexPort
from src.shared.ports.vector_store import VectorStorePort

logger = logging.getLogger(__name__)


class DeleteDocument:
    """Application service for deleting documents and related indexes."""

    def __init__(
        self,
        repository: DocumentRepositoryPort,
        keyword_index: KeywordIndexPort,
        vector_store: VectorStorePort,
    ):
        """Initialize document deletion service."""
        self.repository = repository
        self.keyword_index = keyword_index
        self.vector_store = vector_store

    async def execute(self, request: DeleteDocumentRequest) -> DocumentDeleteResult:
        """Soft-delete a document and clean retrieval indexes.

        Args:
            request: Delete document request

        Returns:
            Document delete result
        """
        logger.info("Deleting document: %s for user: %s", request.document_id, request.user_id)

        try:
            user_id = self._normalize_uuid(request.user_id)
            success = await self.repository.delete_document(
                document_id=request.document_id,
                user_id=user_id,
            )

            if not success:
                return DocumentDeleteResult(
                    document_id=request.document_id,
                    success=False,
                    message="Document not found",
                )

            await self.keyword_index.remove_document(str(user_id), str(request.document_id))
            await self.vector_store.delete_document(request.document_id)

            return DocumentDeleteResult(
                document_id=request.document_id,
                success=True,
                message="Document deleted successfully",
            )

        except Exception as e:
            logger.error("Failed to delete document: %s", e, exc_info=True)
            return DocumentDeleteResult(
                document_id=request.document_id,
                success=False,
                message=f"Delete failed: {str(e)}",
            )

    def _normalize_uuid(self, value: uuid.UUID | str) -> uuid.UUID:
        """Normalize UUID-like values."""
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


__all__ = ["DeleteDocument"]
