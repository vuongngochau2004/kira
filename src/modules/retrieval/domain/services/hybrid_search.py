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

logger = logging.getLogger(__name__)

DEFAULT_RRF_K = 60
DENSE_MULTIPLIER = 2

# Module-level LLM client instance for reranking
_llm_client: Any = None


def set_llm_client(llm_client: Any) -> None:
    """Set the LLM client for hybrid search reranking.

    Args:
        llm_client: LLM client with chat_async method
    """
    global _llm_client
    _llm_client = llm_client


def get_llm_client() -> Any:
    """Get the current LLM client for reranking."""
    return _llm_client


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


async def hybrid_search(
    query_embedding: list[float],
    query_text: str,
    user_id: str | None = None,
    bm25_index: Any = None,
    k: int | None = None,
    rrf_k: int | None = None,
    enable_rerank: bool | None = None,
    dense_search_fn: Any = None,
    bm25_index_class: Any = None,
) -> list[dict]:
    """Hybrid search combining dense and BM25 retrieval with RRF.

    Optionally applies LLM-based reranking for improved precision.

    Args:
        query_embedding: Query vector for dense search
        query_text: Query text for BM25 search
        user_id: Optional user ID filter
        bm25_index: BM25 index instance
        k: Number of final results
        rrf_k: RRF constant
        enable_rerank: Override for reranking
        dense_search_fn: Function for dense search (dependency injection)
        bm25_index_class: BM25Index class (dependency injection)

    Returns:
        Fused list of chunks ranked by RRF score (and reranked if enabled)
    """
    if dense_search_fn is None:
        raise ValueError("hybrid_search requires dense_search_fn dependency")

    k = k or settings.retrieval_k
    rrf_k = rrf_k or settings.rrf_k
    enable_rerank = enable_rerank if enable_rerank is not None else settings.reranking_enabled
    candidate_k = max(k, settings.reranking_top_k_before) if enable_rerank else k

    dense_results = dense_search_fn(
        query_embedding=query_embedding,
        user_id=user_id,
        k=candidate_k * DENSE_MULTIPLIER,
    )
    if asyncio.iscoroutine(dense_results):
        dense_results = await dense_results

    bm25_results = get_bm25_results(bm25_index, query_text, candidate_k)

    logger.debug(
        "Hybrid search composition: dense=%d, bm25=%d, k=%d, candidate_k=%d",
        len(dense_results),
        len(bm25_results),
        k,
        candidate_k,
    )

    if not bm25_results:
        fused = dense_results[:candidate_k]
        logger.debug("Using dense-only retrieval (BM25 unavailable)")
    else:
        dense_formatted = format_dense_results(dense_results)
        fused = reciprocal_rank_fusion([dense_formatted, bm25_results], k=rrf_k)
        fused = fused[:candidate_k]
        logger.debug("RRF fusion completed: %d results", len(fused))

    # Apply reranking if enabled
    if enable_rerank:
        rerank_mode = getattr(settings, "reranking_mode", "llm")
        if rerank_mode == "tei":
            from src.modules.retrieval.domain.services.reranking.tei_reranker import (
                rerank_documents_with_tei,
            )

            fused = await rerank_documents_with_tei(
                query=query_text,
                candidates=fused,
                top_k=k,
                timeout_seconds=settings.reranking_timeout_ms / 1000,
            )
            logger.debug("TEI cross-encoder reranking applied: %d final results", len(fused))
        elif _llm_client is not None:
            fused = await rerank_documents_with_llm(
                query=query_text,
                candidates=fused,
                llm_client=_llm_client,
                top_k=k,
                timeout_seconds=settings.reranking_timeout_ms / 1000,
            )
            logger.debug("LLM reranking applied: %d final results", len(fused))
        else:
            logger.debug(
                "Reranking skipped (no LLM client and reranking_mode is not tei)"
            )
            fused = fused[:k]
    else:
        logger.debug("Reranking disabled")
        fused = fused[:k]

    return fused


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
    "set_llm_client",
    "get_llm_client",
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
