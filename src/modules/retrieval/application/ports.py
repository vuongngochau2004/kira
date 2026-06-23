"""Ports owned by the retrieval application layer."""

from typing import Any, Protocol
from uuid import UUID


class KeywordSearchPort(Protocol):
    """Per-user keyword-index operations needed by hybrid search."""

    def has_documents(self, user_id: str) -> bool: ...

    def get_index(self, user_id: str) -> Any: ...

    def rebuild_from_chunks(self, user_id: str, chunks: list[dict[str, Any]]) -> None: ...


class RetrievalDocumentPort(Protocol):
    """Document metadata and chunks required by retrieval."""

    async def list_completed_chunks(self, user_id: UUID) -> list[dict[str, Any]]: ...

    async def get_filenames(self, document_ids: list[str]) -> dict[str, str]: ...


__all__ = ["KeywordSearchPort", "RetrievalDocumentPort"]
