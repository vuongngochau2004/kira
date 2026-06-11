"""Document deletion use case for application layer."""

import logging
import uuid

from src.modules.document.application.dto import DeleteDocumentRequest, DocumentDeleteResult
from src.modules.document.infrastructure.storage.storage import delete_file, file_exists

logger = logging.getLogger(__name__)


class DeleteDocumentUseCase:
    """Use case for deleting documents."""

    def __init__(self):
        """Initialize delete document use case."""
        pass

    async def execute(self, request: DeleteDocumentRequest) -> DocumentDeleteResult:
        """Execute document deletion use case.

        Args:
            request: Delete document request

        Returns:
            Document delete result
        """
        logger.info("Deleting document: %s for user: %s", request.document_id, request.user_id)

        try:
            # In a full implementation, would:
            # 1. Delete from database (soft delete)
            # 2. Delete chunks from Qdrant
            # 3. Delete from BM25 index
            # 4. Delete file from storage

            # For now, implement storage deletion
            # Would get storage_path from database in real implementation

            document_id_str = str(request.document_id)

            # Example storage path pattern
            user_id_str = str(request.user_id) if isinstance(request.user_id, uuid.UUID) else request.user_id
            possible_storage_paths = [
                f"{user_id_str}/{document_id_str}/",  # Directory pattern
                f"{user_id_str}/{document_id_str}",  # File pattern
            ]

            deleted_any = False
            for storage_path in possible_storage_paths:
                if file_exists(storage_path):
                    delete_file(storage_path)
                    deleted_any = True
                    logger.info("Deleted file from storage: %s", storage_path)

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


__all__ = ["DeleteDocumentUseCase"]
