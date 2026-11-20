"""Port: document persistence contract."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class DocumentRepositoryPort(ABC):
    """Persistence operations required by document application services."""

    @abstractmethod
    async def create_document(
        self,
        user_id: UUID,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ) -> Any:
        """Create a document metadata record."""
        ...

    @abstractmethod
    async def update_document_status(
        self,
        document_id: UUID,
        status: str,
        error_message: str | None = None,
        chunk_count: int = 0,
    ) -> Any | None:
        """Update document processing status."""
        ...

    @abstractmethod
    async def update_document_processing_task(
        self,
        document_id: UUID,
        task_id: str | None,
    ) -> Any | None:
        """Store or clear the background processing task ID."""
        ...

    @abstractmethod
    async def cancel_document(
        self,
        document_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> Any | None:
        """Mark a document as cancelled."""
        ...

    @abstractmethod
    async def get_document(self, document_id: UUID, user_id: UUID | None = None) -> Any | None:
        """Fetch a document by ID, optionally scoped to a user."""
        ...

    @abstractmethod
    async def list_documents(
        self,
        user_id: UUID,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        """List documents for a user."""
        ...

    @abstractmethod
    async def delete_document(self, document_id: UUID, user_id: UUID) -> bool:
        """Soft-delete a document."""
        ...

    @abstractmethod
    async def create_deletion_retry_job(
        self,
        document_id: UUID,
        user_id: UUID,
        storage_path: str | None,
        cleanup_targets: list[str],
        last_error: str,
    ) -> Any:
        """Create a retry job for failed external document cleanup."""
        ...

    @abstractmethod
    async def create_chunks(self, document_id: UUID, chunks: list[dict]) -> list[Any]:
        """Persist document chunks."""
        ...

    @abstractmethod
    async def get_document_chunks(self, document_id: UUID) -> list[Any]:
        """Fetch chunks for a document."""
        ...


__all__ = ["DocumentRepositoryPort"]
