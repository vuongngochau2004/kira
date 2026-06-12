"""Document deletion application service."""

import logging
import uuid
from collections.abc import Awaitable, Callable

from src.modules.document.application.dto import DeleteDocumentRequest, DocumentDeleteResult
from src.shared.ports.document_repository import DocumentRepositoryPort
from src.shared.ports.keyword_index import KeywordIndexPort
from src.shared.ports.storage import StoragePort
from src.shared.ports.vector_store import VectorStorePort

logger = logging.getLogger(__name__)


class DeleteDocument:
    """Application service for deleting documents and related indexes."""

    def __init__(
        self,
        repository: DocumentRepositoryPort,
        keyword_index: KeywordIndexPort,
        vector_store: VectorStorePort,
        storage: StoragePort,
    ):
        """Initialize document deletion service."""
        self.repository = repository
        self.keyword_index = keyword_index
        self.vector_store = vector_store
        self.storage = storage

    async def execute(self, request: DeleteDocumentRequest) -> DocumentDeleteResult:
        """Soft-delete a document and clean external indexes/storage.

        Args:
            request: Delete document request

        Returns:
            Document delete result
        """
        logger.info("Deleting document: %s for user: %s", request.document_id, request.user_id)

        try:
            user_id = self._normalize_uuid(request.user_id)
            document = await self.repository.get_document(
                document_id=request.document_id,
                user_id=user_id,
            )
            if not document:
                return DocumentDeleteResult(
                    document_id=request.document_id,
                    success=False,
                    message="Document not found",
                )

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

            cleanup_errors = await self._cleanup_external_resources(
                user_id=user_id,
                document_id=request.document_id,
                storage_path=document.storage_path,
            )
            if cleanup_errors:
                retry_job_created = await self._queue_cleanup_retry(
                    document_id=request.document_id,
                    user_id=user_id,
                    storage_path=document.storage_path,
                    cleanup_errors=cleanup_errors,
                )
                logger.warning(
                    "Document %s soft-deleted; cleanup retry queued for targets: %s",
                    request.document_id,
                    ", ".join(cleanup_errors.keys()),
                )
                return DocumentDeleteResult(
                    document_id=request.document_id,
                    success=True,
                    message=(
                        "Document deleted; cleanup retry queued"
                        if retry_job_created
                        else "Document deleted; cleanup retry queue failed"
                    ),
                )

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

    async def _cleanup_external_resources(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        storage_path: str | None,
    ) -> dict[str, str]:
        """Attempt external cleanup and return failed targets."""
        errors: dict[str, str] = {}

        cleanup_steps: list[tuple[str, Callable[[], Awaitable[None]]]] = [
            ("bm25", lambda: self.keyword_index.remove_document(str(user_id), str(document_id))),
            ("qdrant", lambda: self.vector_store.delete_document(document_id)),
        ]
        if storage_path:
            cleanup_steps.append(("minio", lambda: self.storage.delete(storage_path)))

        for target, cleanup in cleanup_steps:
            try:
                await cleanup()
            except Exception as exc:
                logger.error(
                    "Failed to clean %s for document %s: %s",
                    target,
                    document_id,
                    exc,
                    exc_info=True,
                )
                errors[target] = str(exc)

        return errors

    async def _queue_cleanup_retry(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        storage_path: str | None,
        cleanup_errors: dict[str, str],
    ) -> bool:
        """Persist a retry job for failed cleanup targets."""
        try:
            await self.repository.create_deletion_retry_job(
                document_id=document_id,
                user_id=user_id,
                storage_path=storage_path,
                cleanup_targets=list(cleanup_errors.keys()),
                last_error="; ".join(
                    f"{target}: {error}" for target, error in cleanup_errors.items()
                ),
            )
            return True
        except Exception as exc:
            logger.error(
                "Document %s soft-deleted, but cleanup retry job could not be queued: %s",
                document_id,
                exc,
                exc_info=True,
            )
            return False

    def _normalize_uuid(self, value: uuid.UUID | str) -> uuid.UUID:
        """Normalize UUID-like values."""
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


__all__ = ["DeleteDocument"]
