"""Adapters that provide retrieval application ports."""

from typing import Any
from uuid import UUID

from src.modules.retrieval.infrastructure.document_store.document_repository import (
    get_documents_batch,
    list_completed_chunks_for_user,
)
from src.modules.retrieval.infrastructure.keyword.bm25_manager import BM25IndexManager


class BM25KeywordSearchAdapter:
    """Expose the in-memory BM25 manager through the retrieval application port."""

    def __init__(self, manager: BM25IndexManager):
        self._manager = manager

    def has_documents(self, user_id: str) -> bool:
        return self._manager.has_documents(user_id)

    def get_index(self, user_id: str) -> Any:
        return self._manager.get_index(user_id)

    def rebuild_from_chunks(self, user_id: str, chunks: list[dict[str, Any]]) -> None:
        self._manager.rebuild_from_chunks(user_id=user_id, all_chunks=chunks)


class PostgresRetrievalDocumentAdapter:
    """Expose Postgres retrieval metadata through the retrieval application port."""

    async def list_completed_chunks(self, user_id: UUID) -> list[dict[str, Any]]:
        return await list_completed_chunks_for_user(user_id)

    async def get_filenames(self, document_ids: list[str]) -> dict[str, str]:
        return await get_documents_batch(document_ids)


__all__ = ["BM25KeywordSearchAdapter", "PostgresRetrievalDocumentAdapter"]
