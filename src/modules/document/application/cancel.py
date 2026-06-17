"""Document cancellation application service."""

import logging
import uuid
from collections.abc import Awaitable, Callable

from src.constants import DocumentStatus
from src.modules.document.application.dto import CancelDocumentRequest, DocumentCancelResult
from src.shared.ports.document_repository import DocumentRepositoryPort
from src.shared.ports.keyword_index import KeywordIndexPort
from src.shared.ports.storage import StoragePort
from src.shared.ports.vector_store import VectorStorePort
from src.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


class CancelDocument:
    """Application service for cancelling document upload/processing work."""

    def __init__(
        self,
        repository: DocumentRepositoryPort,
        keyword_index: KeywordIndexPort,
        vector_store: VectorStorePort,
        storage: StoragePort,
    ):
        """Initialize document cancellation service."""
        self.repository = repository
        self.keyword_index = keyword_index
        self.vector_store = vector_store
        self.storage = storage

    async def execute(self, request: CancelDocumentRequest) -> DocumentCancelResult:
        """Cancel a document processing task and clean partial resources."""
        user_id = self._normalize_uuid(request.user_id)
        logger.info("Cancelling document: %s for user: %s", request.document_id, user_id)

        document = await self.repository.get_document(
            document_id=request.document_id,
            user_id=user_id,
        )
        if not document:
            return DocumentCancelResult(
                document_id=request.document_id,
                success=False,
                message="Document not found",
            )

        if document.status == DocumentStatus.COMPLETED.value:
            return DocumentCancelResult(
                document_id=request.document_id,
                success=False,
                message="Completed documents cannot be cancelled",
            )

        if document.status == DocumentStatus.CANCELLED.value:
            return DocumentCancelResult(
                document_id=request.document_id,
                success=True,
                message="Document already cancelled",
                status=DocumentStatus.CANCELLED.value,
            )

        task_id = getattr(document, "processing_task_id", None)
        if task_id:
            self._revoke_processing_task(task_id)

        cancelled = await self.repository.cancel_document(
            document_id=request.document_id,
            user_id=user_id,
            reason="Processing cancelled by user",
        )
        if not cancelled:
            return DocumentCancelResult(
                document_id=request.document_id,
                success=False,
                message="Document could not be cancelled",
            )

        cleanup_errors = await self._cleanup_external_resources(
            user_id=user_id,
            document_id=request.document_id,
            storage_path=document.storage_path,
        )

        if cleanup_errors:
            logger.warning(
                "Document %s cancelled; cleanup failed for targets: %s",
                request.document_id,
                ", ".join(cleanup_errors.keys()),
            )
            return DocumentCancelResult(
                document_id=request.document_id,
                success=True,
                message="Document cancelled; cleanup partially failed",
                status=DocumentStatus.CANCELLED.value,
                cleanup_errors=cleanup_errors,
            )

        return DocumentCancelResult(
            document_id=request.document_id,
            success=True,
            message="Document cancelled",
            status=DocumentStatus.CANCELLED.value,
        )

    def _revoke_processing_task(self, task_id: str) -> None:
        """Ask Celery to revoke a queued/running processing task."""
        try:
            celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
        except Exception as exc:
            logger.warning("Failed to revoke document task %s: %s", task_id, exc, exc_info=True)

    async def _cleanup_external_resources(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        storage_path: str | None,
    ) -> dict[str, str]:
        """Attempt cleanup for resources that may have been partially created."""
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
                    "Failed to clean %s for cancelled document %s: %s",
                    target,
                    document_id,
                    exc,
                    exc_info=True,
                )
                errors[target] = str(exc)

        return errors

    def _normalize_uuid(self, value: uuid.UUID | str) -> uuid.UUID:
        """Normalize UUID-like values."""
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


__all__ = ["CancelDocument"]
