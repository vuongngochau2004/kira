"""Hybrid retrieval combining dense and BM25 with Reciprocal Rank Fusion (RRF).

Supports optional LLM-based reranking for improved precision.
"""

import asyncio
import json
import logging
import re
from collections import defaultdict
from typing import Any

from src.config.config import settings
from src.modules.retrieval.domain.prompts import RERANKING_SYSTEM_PROMPT, build_reranking_prompt


logger = logging.getLogger(__name__)

DEFAULT_RRF_K = 60
DENSE_MULTIPLIER = 2

# Global LLM client for reranking
_llm_client: Any = None


def set_llm_client(llm_client: Any) -> None:
    """Set the global LLM client for reranking.

    Args:
        llm_client: LLM client with chat_async method
    """
    global _llm_client
    _llm_client = llm_client


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
    doc_id = item.get("document_id") or item.get("metadata", {}).get("document_id", "")
    chunk_idx = item.get("chunk_index")
    if chunk_idx is None:
        chunk_idx = item.get("metadata", {}).get("chunk_index", "")
    return f"{doc_id}_{chunk_idx}"


def _build_sorted_results(
    doc_map: dict[str, dict],
    scores: dict[str, float],
) -> list[dict]:
    """Build sorted results with RRF scores and standardized structure."""
    results = []
    for key, rrf_score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        doc = doc_map[key].copy()
        doc["rrf_score"] = rrf_score

        # Ensure standardized fields
        if "text" not in doc:
            doc["text"] = doc.get("content", "")
        if "content" not in doc:
            doc["content"] = doc.get("text", "")

        results.append(doc)
    return results


async def hybrid_search(
    query_embedding: list[float],
    query_text: str,
    user_id: str | None = None,
    bm25_index=None,
    k: int | None = None,
    rrf_k: int | None = None,
    enable_rerank: bool | None = None,
    dense_search_fn=None,
    bm25_index_class=None,
) -> list[dict]:
    """Hybrid search combining dense and BM25 retrieval with RRF.

    Optionally applies LLM-based reranking for improved precision.

    Args:
        query_embedding: Query vector for dense search
        query_text: Query text for BM25 search
        user_id: Optional user ID filter
        bm25_index: BM25 index (optional, falls back to dense only)
        k: Number of final results
        rrf_k: RRF constant
        enable_rerank: Override for reranking (None = use setting)
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

    bm25_results = _get_bm25_results(bm25_index, query_text, candidate_k)

    # ✅ Log retrieval composition for debugging
    logger.debug(
        f"Hybrid search composition: dense={len(dense_results)}, "
        f"bm25={len(bm25_results)}, k={k}, candidate_k={candidate_k}"
    )

    if not bm25_results:
        fused = dense_results[:candidate_k]
        logger.debug("Using dense-only retrieval (BM25 unavailable)")
    else:
        dense_formatted = _format_dense_results(dense_results)
        fused = reciprocal_rank_fusion([dense_formatted, bm25_results], k=rrf_k)
        fused = fused[:candidate_k]
        logger.debug(f"RRF fusion completed: {len(fused)} results")

    # Apply LLM reranking if enabled
    if enable_rerank and _llm_client is not None:
        fused = await _apply_llm_reranking(query_text, fused, k)
        logger.debug(f"LLM reranking applied: {len(fused)} final results")
    else:
        logger.debug(
            f"LLM reranking {'disabled' if not enable_rerank else 'skipped (no LLM client)'}"
        )
        fused = fused[:k]

    return fused


async def _apply_llm_reranking(
    query: str,
    documents: list[dict],
    top_k: int,
) -> list[dict]:
    """Apply LLM-based reranking to documents.

    Args:
        query: Search query
        documents: Retrieved documents to rerank
        top_k: Number of top results to return

    Returns:
        Reranked list of documents
    """
    if not documents or len(documents) <= top_k:
        return documents

    rerank_k = settings.reranking_top_k_before
    candidates = documents[:rerank_k]

    # Build reranking prompt
    prompt = _build_reranking_prompt(query, candidates)

    try:
        # Call LLM directly (no more async bridge needed)
        llm_response = await _call_llm_for_reranking(prompt)

        # Parse and reorder documents
        ranked_indices = _parse_llm_reranking(llm_response, len(candidates))
        reranked = _reorder_by_indices(candidates, ranked_indices, top_k)

        logger.debug(f"Reranked {len(reranked)} documents from {len(candidates)} candidates")
        return reranked

    except Exception as e:
        logger.error(f"LLM reranking failed: {e}")
        return documents[:top_k]


def _build_reranking_prompt(query: str, candidates: list[dict]) -> str:
    """Build LLM prompt for document reranking.

    Args:
        query: Search query
        candidates: Documents to rerank

    Returns:
        Formatted prompt string
    """
    return build_reranking_prompt(query, _format_docs_for_llm(candidates))


async def _call_llm_for_reranking(prompt: str) -> str:
    """Call LLM for reranking with timeout.

    Args:
        prompt: Reranking prompt

    Returns:
        LLM response content

    Raises:
        Exception: If LLM call fails or times out
    """
    messages = [
        {"role": "system", "content": RERANKING_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    response = await asyncio.wait_for(
        _llm_client.chat_async(
            messages=messages,
            temperature=0.1,
            max_tokens=256,
        ),
        timeout=settings.reranking_timeout_ms / 1000,
    )

    return response.get("content", "")


def _reorder_by_indices(
    candidates: list[dict],
    indices: list[int],
    top_k: int,
) -> list[dict]:
    """Reorder documents by ranked indices with deduplication.

    Args:
        candidates: Original documents
        indices: Ranked indices from LLM
        top_k: Maximum results to return

    Returns:
        Reordered list of documents
    """
    reranked = []
    seen = set()

    for idx in indices:
        if idx in seen or idx >= len(candidates) or idx < 0:
            continue
        reranked.append(candidates[idx])
        seen.add(idx)

    # Add any missed documents
    for idx, doc in enumerate(candidates):
        if idx not in seen and len(reranked) < top_k:
            reranked.append(doc)

    return reranked[:top_k]


def _format_docs_for_llm(documents: list[dict]) -> str:
    """Format documents for LLM reranking prompt.

    Args:
        documents: List of document dicts

    Returns:
        Formatted string
    """
    formatted = []
    for idx, doc in enumerate(documents):
        text = doc.get("text", doc.get("content")) or ""
        text_preview = text[:800] + "..." if len(text) > 800 else text
        formatted.append(f"[{idx}] {text_preview}")

    return "\n\n".join(formatted)


def _parse_llm_reranking(response: str, num_documents: int) -> list[int]:
    """Parse LLM response to extract ranked indices.

    Args:
        response: LLM response string
        num_documents: Number of documents for validation

    Returns:
        List of ranked indices
    """
    # Try to extract JSON array
    try:
        json_match = re.search(r"\[.*?\]", response)
        if json_match:
            indices = json.loads(json_match.group(0))
            if isinstance(indices, list):
                return [int(i) for i in indices]
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: extract comma-separated numbers
    numbers = re.findall(r"\d+", response)
    if numbers:
        return [int(n) for n in numbers]

    # Last resort: return original order
    return list(range(num_documents))


def _get_bm25_results(
    bm25_index,
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
            "document_id": doc.get("document_id") or doc.get("metadata", {}).get("document_id"),
            "chunk_index": doc.get("chunk_index")
            if doc.get("chunk_index") is not None
            else doc.get("metadata", {}).get("chunk_index"),
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


__all__ = ["reciprocal_rank_fusion", "hybrid_search", "set_llm_client"]
