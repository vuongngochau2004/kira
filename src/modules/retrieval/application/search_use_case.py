"""Search use case for retrieval operations.

Orchestrates hybrid search combining dense and BM25 retrieval with RRF fusion.
"""

from typing import Any

from src.modules.retrieval.domain.services.hybrid_search import hybrid_search


class SearchUseCase:
    """Use case for search operations.

    Orchestrates retrieval by combining:
    - Dense vector search (Qdrant)
    - BM25 keyword search
    - RRF fusion
    - Optional LLM reranking
    """

    def __init__(self, bm25_index_getter=None, llm_client=None):
        """Initialize search use case.

        Args:
            bm25_index_getter: Function to get BM25 index for user
            llm_client: Optional LLM client for reranking
        """
        self._get_bm25_index = bm25_index_getter
        self._llm_client = llm_client

        # Set LLM client for reranking in hybrid_search
        if llm_client is not None:
            from src.modules.retrieval.domain.services.hybrid_search import set_llm_client
            set_llm_client(llm_client)

    async def execute(
        self,
        query_embedding: list[float],
        query_text: str,
        user_id: str | None = None,
        k: int = 5,
        rrf_k: int = 60,
        enable_rerank: bool = False,
    ) -> list[dict]:
        """Execute hybrid search.

        Args:
            query_embedding: Query vector for dense search
            query_text: Query text for BM25 search
            user_id: Optional user ID filter
            k: Number of final results
            rrf_k: RRF constant
            enable_rerank: Enable LLM reranking

        Returns:
            Fused list of chunks ranked by RRF score (and reranked if enabled)
        """
        # Get BM25 index for user
        bm25_index = None
        if self._get_bm25_index is not None and user_id is not None:
            bm25_index = self._get_bm25_index(user_id)

        # Execute hybrid search
        results = await hybrid_search(
            query_embedding=query_embedding,
            query_text=query_text,
            user_id=user_id,
            bm25_index=bm25_index,
            k=k,
            rrf_k=rrf_k,
            enable_rerank=enable_rerank,
        )

        return results


__all__ = ["SearchUseCase"]
