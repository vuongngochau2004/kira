"""Hybrid retrieval combining dense vector search and BM25 with RRF and LLM reranking."""

import asyncio
import logging
from typing import Any

from src.config.config import settings
from src.modules.retrieval.domain.services.fusion import reciprocal_rank_fusion
from src.modules.retrieval.domain.services.reranking.llm_reranker import (
    format_documents_for_reranking,
    parse_reranking_response,
    reorder_by_indices,
    rerank_documents_with_llm,
    run_llm_rerank,
)
from src.modules.retrieval.domain.services.reranking.tei_reranker import (
    rerank_documents_with_tei,
)

logger = logging.getLogger(__name__)

DEFAULT_RRF_K = 60
DENSE_MULTIPLIER = 2


def get_bm25_results(
    bm25_index: Any,
    query_text: str,
    k: int,
) -> list[dict]:
    """Get candidate results from BM25 index."""
    if not bm25_index:
        return []

    bm25_docs = bm25_index.search(query_text, k=k * DENSE_MULTIPLIER)
    return [
        {
            "text": doc.get("content", ""),
            "content": doc.get("content", ""),
            "metadata": doc.get("metadata", {}),
            "score": doc.get("score", 0),
            "document_id": doc.get("document_id") or doc.get("metadata", {}).get("document_id"),
            "chunk_index": doc.get("chunk_index")
            if doc.get("chunk_index") is not None
            else doc.get("metadata", {}).get("chunk_index"),
        }
        for doc in bm25_docs
    ]


def format_dense_results(dense_results: list[dict]) -> list[dict]:
    """Format dense search results for fusion."""
    return [
        {
            "text": item.get("text", ""),
            "content": item.get("text", ""),
            "metadata": {
                "document_id": item.get("document_id"),
                "user_id": item.get("user_id"),
                "chunk_index": item.get("chunk_index"),
            },
            "score": item.get("score", 0),
            "document_id": item.get("document_id"),
            "chunk_index": item.get("chunk_index"),
        }
        for item in dense_results
    ]


async def hybrid_search_candidates(
    query_embedding: list[float],
    query_text: str,
    user_id: str | None = None,
    bm25_index: Any = None,
    k: int | None = None,
    rrf_k: int | None = None,
    dense_search_fn: Any = None,
) -> list[dict]:
    """Collect fused candidates before the selected reranking adapter runs.

    Args:
        query_embedding: Query vector for dense search
        query_text: Query text for BM25 search
        user_id: Optional user ID filter
        bm25_index: BM25 index instance
        k: Number of candidates
        rrf_k: RRF constant
        dense_search_fn: Function for dense search (dependency injection)

    Returns:
        Fused list of chunks ranked by RRF score
    """
    if dense_search_fn is None:
        raise ValueError("hybrid_search_candidates requires dense_search_fn dependency")

    k = k or settings.retrieval_k
    rrf_k = rrf_k or settings.rrf_k
    dense_results = dense_search_fn(
        query_embedding=query_embedding,
        user_id=user_id,
        k=k * DENSE_MULTIPLIER,
    )
    if asyncio.iscoroutine(dense_results):
        dense_results = await dense_results

    bm25_results = get_bm25_results(bm25_index, query_text, k)

    logger.debug(
        "Hybrid search composition: dense=%d, bm25=%d, candidate_k=%d",
        len(dense_results),
        len(bm25_results),
        k,
    )

    if not bm25_results:
        fused = dense_results[:k]
        logger.debug("Using dense-only retrieval (BM25 unavailable)")
    else:
        dense_formatted = format_dense_results(dense_results)
        fused = reciprocal_rank_fusion([dense_formatted, bm25_results], k=rrf_k)
        fused = fused[:k]
        logger.debug("RRF fusion completed: %d results", len(fused))

    return fused


async def hybrid_search(
    query_embedding: list[float],
    query_text: str,
    user_id: str | None = None,
    bm25_index: Any = None,
    k: int | None = None,
    rrf_k: int | None = None,
    llm_client: Any = None,
    dense_search_fn: Any = None,
) -> list[dict]:
    """Return fused search results reranked by the configured adapter."""
    k = k or settings.retrieval_k
    candidates = await hybrid_search_candidates(
        query_embedding=query_embedding,
        query_text=query_text,
        user_id=user_id,
        bm25_index=bm25_index,
        k=max(k, settings.reranking_top_k_before),
        rrf_k=rrf_k,
        dense_search_fn=dense_search_fn,
    )
    if settings.reranking_mode == "tei":
        return await rerank_documents_with_tei(
            query=query_text,
            candidates=candidates,
            top_k=k,
            timeout_seconds=settings.reranking_timeout_ms / 1000,
        )
    if llm_client is None:
        raise RuntimeError("LLM reranker is not configured")
    return await rerank_documents_with_llm(
        query=query_text,
        candidates=candidates,
        llm_client=llm_client,
        top_k=k,
        timeout_seconds=settings.reranking_timeout_ms / 1000,
    )


# Backward compatibility private aliases
_get_bm25_results = get_bm25_results
_format_dense_results = format_dense_results
_format_docs_for_llm = format_documents_for_reranking
_parse_llm_reranking = parse_reranking_response
_reorder_by_indices = reorder_by_indices
_call_llm_for_reranking = run_llm_rerank
_apply_llm_reranking = rerank_documents_with_llm

__all__ = [
    "DENSE_MULTIPLIER",
    "hybrid_search",
    "hybrid_search_candidates",
    "get_bm25_results",
    "format_dense_results",
    "_get_bm25_results",
    "_format_dense_results",
    "_format_docs_for_llm",
    "_parse_llm_reranking",
    "_reorder_by_indices",
    "_call_llm_for_reranking",
    "_apply_llm_reranking",
]
