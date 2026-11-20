"""Dependency composition for the retrieval module."""

from kira.providers.vector.qdrant import QdrantAdapter
from kira.retrieval.adapters import (
    BM25KeywordSearchAdapter,
    PostgresRetrievalDocumentAdapter,
)
from kira.retrieval.bm25_manager import get_bm25_manager
from kira.retrieval.search import SearchUseCase


def create_search_use_case(llm_client=None) -> SearchUseCase:
    """Compose the default search use case."""
    bm25_manager = get_bm25_manager()
    return SearchUseCase(
        vector_store=QdrantAdapter(),
        keyword_search=BM25KeywordSearchAdapter(bm25_manager),
        documents=PostgresRetrievalDocumentAdapter(),
        llm_client=llm_client,
    )


__all__ = ["create_search_use_case"]
