"""BM25 keyword index adapter."""

from uuid import UUID

from src.modules.retrieval.infrastructure.keyword.bm25_manager import BM25IndexManager
from src.shared.ports.keyword_index import KeywordIndexPort


class BM25KeywordIndexAdapter(KeywordIndexPort):
    """Adapter around the in-memory BM25 index manager."""

    def __init__(self, manager: BM25IndexManager):
        """Initialize adapter with a concrete BM25 manager."""
        self.manager = manager

    async def add_document_bulk(self, user_id: UUID | str, chunks: list[dict]) -> None:
        """Add document chunks to the user's keyword index."""
        self.manager.add_document_bulk(user_id=user_id, chunks=chunks)

    async def remove_document(self, user_id: UUID | str, document_id: UUID | str) -> None:
        """Remove a document from the user's keyword index."""
        self.manager.remove_document(user_id=user_id, document_id=document_id)


__all__ = ["BM25KeywordIndexAdapter"]
