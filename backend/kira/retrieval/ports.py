"""Ports owned by the retrieval application layer."""

from typing import Any, Protocol
from uuid import UUID


class KeywordSearchPort(Protocol):
    """Per-user keyword-index operations needed by hybrid search."""

    def has_documents(self, user_id: str) -> bool: ...

    def get_index(self, user_id: str) -> Any: ...

    def get_signature(self, user_id: str) -> Any:
        """Signature of the chunk set the user's index was last built from (None if unknown)."""
        ...

    def rebuild_from_chunks(
        self, user_id: str, chunks: list[dict[str, Any]], signature: Any = None
    ) -> None: ...


class RetrievalDocumentPort(Protocol):
    """Document metadata and chunks required by retrieval."""

    async def list_completed_chunks(self, user_id: UUID) -> list[dict[str, Any]]: ...

    async def completed_chunks_signature(self, user_id: UUID) -> Any:
        """Cheap fingerprint that changes whenever list_completed_chunks would change."""
        ...

    async def get_filenames(self, document_ids: list[str]) -> dict[str, str]: ...


__all__ = ["KeywordSearchPort", "RetrievalDocumentPort"]
