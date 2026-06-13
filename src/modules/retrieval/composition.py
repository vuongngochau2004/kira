"""Dependency composition for the retrieval module."""

from src.modules.retrieval.application.search_use_case import SearchUseCase
from src.modules.retrieval.infrastructure.document_store.document_repository import (
    list_completed_chunks_for_user,
)
from src.modules.retrieval.infrastructure.keyword.bm25_manager import get_bm25_manager
from src.shared.adapters.vector.qdrant_adapter import QdrantAdapter


def create_search_use_case(llm_client=None) -> SearchUseCase:
    """Compose the default search use case."""
    bm25_manager = get_bm25_manager()
    return SearchUseCase(
        vector_store=QdrantAdapter(),
        bm25_index_getter=bm25_manager.get_index,
        bm25_manager=bm25_manager,
        bm25_rebuild_loader=list_completed_chunks_for_user,
        llm_client=llm_client,
    )


__all__ = ["create_search_use_case"]
