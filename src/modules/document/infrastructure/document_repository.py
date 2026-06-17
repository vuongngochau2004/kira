"""SQLAlchemy document repository adapter."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.retrieval.infrastructure.document_store import document_repository
from src.shared.ports.document_repository import DocumentRepositoryPort


class SqlAlchemyDocumentRepository(DocumentRepositoryPort):
    """Adapter that implements document persistence with SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with a request/session scoped DB session."""
        self.db = db

    async def create_document(
        self,
        user_id: UUID,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ) -> Any:
        """Create a document metadata record."""
        return await document_repository.create_document(
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=storage_path,
            db=self.db,
        )

    async def update_document_status(
        self,
        document_id: UUID,
        status: str,
        error_message: str | None = None,
        chunk_count: int = 0,
    ) -> Any | None:
        """Update document processing status."""
        return await document_repository.update_document_status(
            document_id=document_id,
            status=status,
            error_message=error_message,
            chunk_count=chunk_count,
            db=self.db,
        )

    async def update_document_processing_task(
        self,
        document_id: UUID,
        task_id: str | None,
    ) -> Any | None:
        """Store or clear the Celery task ID for a document."""
        return await document_repository.update_document_processing_task(
            document_id=document_id,
            task_id=task_id,
            db=self.db,
        )

    async def cancel_document(
        self,
        document_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> Any | None:
        """Mark a document as cancelled."""
        return await document_repository.cancel_document(
            document_id=document_id,
            user_id=user_id,
            reason=reason,
            db=self.db,
        )

    async def get_document(self, document_id: UUID, user_id: UUID | None = None) -> Any | None:
        """Fetch a document by ID, optionally scoped to a user."""
        return await document_repository.get_document(
            document_id=document_id,
            user_id=user_id,
            db=self.db,
        )

    async def list_documents(
        self,
        user_id: UUID,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        """List documents for a user."""
        return await document_repository.list_documents(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
            db=self.db,
        )

    async def delete_document(self, document_id: UUID, user_id: UUID) -> bool:
        """Soft-delete a document."""
        return await document_repository.delete_document(
            document_id=document_id,
            user_id=user_id,
            db=self.db,
        )

    async def create_deletion_retry_job(
        self,
        document_id: UUID,
        user_id: UUID,
        storage_path: str | None,
        cleanup_targets: list[str],
        last_error: str,
    ) -> Any:
        """Create a retry job for failed external document cleanup."""
        return await document_repository.create_deletion_retry_job(
            document_id=document_id,
            user_id=user_id,
            storage_path=storage_path,
            cleanup_targets=cleanup_targets,
            last_error=last_error,
            db=self.db,
        )

    async def create_chunks(self, document_id: UUID, chunks: list[dict]) -> list[Any]:
        """Persist document chunks."""
        return await document_repository.create_chunks(
            document_id=document_id,
            chunks=chunks,
            db=self.db,
        )

    async def get_document_chunks(self, document_id: UUID) -> list[Any]:
        """Fetch chunks for a document."""
        return await document_repository.get_document_chunks(
            document_id=document_id,
            db=self.db,
        )


__all__ = ["SqlAlchemyDocumentRepository"]
