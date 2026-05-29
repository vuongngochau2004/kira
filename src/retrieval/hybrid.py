"""Hybrid retrieval combining dense and BM25 with Reciprocal Rank Fusion (RRF)."""

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.config import settings
from src.retrieval.dense import dense_search
from src.retrieval.bm25 import BM25Index

DEFAULT_RRF_K = 60
DENSE_MULTIPLIER = 2


def reciprocal_rank_fusion(
    ranked_results: list[list[dict]],
    k: int = DEFAULT_RRF_K,
) -> list[dict]:
    """Reciprocal Rank Fusion for combining multiple ranked lists.

    Args:
        ranked_results: List of ranked results from different retrieval methods
        k: RRF constant (higher = more balanced ranking)

    Returns:
        Fused and re-ranked list of dicts with rrf_score
    """
    scores: dict[str, float] = defaultdict(float)
    doc_map: dict[str, dict] = {}

    for results in ranked_results:
        for rank, item in enumerate(results):
            key = _make_doc_key(item)
            doc_map[key] = item
            scores[key] += 1 / (k + rank + 1)

    return _build_sorted_results(doc_map, scores)


def _make_doc_key(item: dict) -> str:
    """Create unique key from document metadata."""
    doc_id = item.get("document_id", "")
    chunk_idx = item.get("chunk_index", item.get("metadata", {}).get("chunk_index", ""))
    return f"{doc_id}_{chunk_idx}"


def _build_sorted_results(
    doc_map: dict[str, dict],
    scores: dict[str, float],
) -> list[dict]:
    """Build sorted results with RRF scores."""
    results = []
    for key, rrf_score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        doc = doc_map[key].copy()
        doc["rrf_score"] = rrf_score
        results.append(doc)
    return results


def hybrid_search(
    query_embedding: list[float],
    query_text: str,
    user_id: str | None = None,
    bm25_index: BM25Index | None = None,
    k: int | None = None,
    rrf_k: int | None = None,
) -> list[dict]:
    """Hybrid search combining dense and BM25 retrieval with RRF.

    Args:
        query_embedding: Query vector for dense search
        query_text: Query text for BM25 search
        user_id: Optional user ID filter
        bm25_index: BM25 index (optional, falls back to dense only)
        k: Number of final results
        rrf_k: RRF constant

    Returns:
        Fused list of chunks ranked by RRF score
    """
    k = k or settings.retrieval_k
    rrf_k = rrf_k or settings.rrf_k

    dense_results = dense_search(
        query_embedding=query_embedding,
        user_id=user_id,
        k=k * DENSE_MULTIPLIER,
    )

    bm25_results = _get_bm25_results(bm25_index, query_text, k)

    if not bm25_results:
        return dense_results[:k]

    dense_formatted = _format_dense_results(dense_results)
    fused = reciprocal_rank_fusion([dense_formatted, bm25_results], k=rrf_k)

    return fused[:k]


def _get_bm25_results(
    bm25_index: BM25Index | None,
    query_text: str,
    k: int,
) -> list[dict]:
    """Get BM25 search results."""
    if not bm25_index:
        return []

    bm25_docs = bm25_index.search(query_text, k=k * DENSE_MULTIPLIER)
    return [
        {
            "text": doc.get("content", ""),
            "content": doc.get("content", ""),
            "metadata": doc.get("metadata", {}),
            "score": doc.get("score", 0),
        }
        for doc in bm25_docs
    ]


def _format_dense_results(dense_results: list[dict]) -> list[dict]:
    """Format dense results for fusion."""
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


__all__ = ["reciprocal_rank_fusion", "hybrid_search"]
