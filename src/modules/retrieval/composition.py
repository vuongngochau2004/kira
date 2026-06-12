"""Dependency composition for the retrieval module."""

from src.modules.retrieval.application.search_use_case import SearchUseCase
from src.modules.retrieval.infrastructure.keyword.bm25_manager import get_bm25_manager
from src.shared.adapters.vector.qdrant_adapter import QdrantAdapter


def create_search_use_case(llm_client=None) -> SearchUseCase:
    """Compose the default search use case."""
    return SearchUseCase(
        vector_store=QdrantAdapter(),
        bm25_index_getter=get_bm25_manager().get_index,
        llm_client=llm_client,
    )


__all__ = ["create_search_use_case"]
