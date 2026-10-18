"""TEI Cross-Encoder Reranker adapter for DUT AI.

Calls the Hugging Face Text Embeddings Inference (TEI) /rerank endpoint
serving BAAI/bge-reranker-v2-m3 for high-speed, high-accuracy cross-encoder reranking.
"""

import logging
from typing import Any

import httpx

from src.config.config import settings

logger = logging.getLogger(__name__)


def extract_document_text(doc: dict[str, Any]) -> str:
    """Extract text content from candidate document dictionary."""
    if "text" in doc and doc["text"]:
        return str(doc["text"])
    if "content" in doc and doc["content"]:
        return str(doc["content"])
    metadata = doc.get("metadata")
    if isinstance(metadata, dict) and metadata.get("text"):
        return str(metadata["text"])
    return ""


async def rerank_documents_with_tei(
    query: str,
    candidates: list[dict[str, Any]],
    top_k: int = 5,
    timeout_seconds: float = 10.0,
    base_url: str | None = None,
    api_key: str | None = None,
    min_score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    """Rerank candidate documents using TEI Cross-Encoder (/rerank endpoint).

    Args:
        query: User search query
        candidates: List of retrieved document dictionaries
        top_k: Number of top documents to return
        timeout_seconds: Request timeout in seconds
        base_url: Optional override for TEI base URL
        api_key: Optional override for TEI API key
        min_score_threshold: Minimum score threshold to keep candidates

    Returns:
        List of reranked candidates sorted by cross-encoder score
    """
    if not candidates:
        return []

    if len(candidates) <= 1:
        return candidates[:top_k]

    target_url = (base_url or settings.tei_base_url).rstrip("/")
    token = api_key or settings.tei_api_key
    threshold = (
        min_score_threshold
        if min_score_threshold is not None
        else settings.reranking_min_score_threshold
    )

    texts = [extract_document_text(c) for c in candidates]

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "query": query,
        "texts": texts,
        "return_text": False,
    }

    rerank_endpoint = f"{target_url}/rerank"

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(rerank_endpoint, json=payload, headers=headers)
            response.raise_for_status()
            results = response.json()

        # Expected format: [{"index": int, "score": float}, ...]
        if not isinstance(results, list):
            logger.warning("Unexpected TEI rerank response format: %s", type(results))
            return candidates[:top_k]

        reranked: list[dict[str, Any]] = []
        for item in results:
            idx = item.get("index")
            score = item.get("score", 0.0)
            if idx is not None and 0 <= idx < len(candidates):
                candidate = dict(candidates[idx])
                candidate["rerank_score"] = float(score)
                # Filter by threshold if threshold is configured and we still have candidates
                if threshold is None or score >= threshold or not reranked:
                    reranked.append(candidate)

        # In case all items were filtered out, preserve at least the highest scored one
        if not reranked and results:
            best_idx = results[0].get("index", 0)
            if 0 <= best_idx < len(candidates):
                best_cand = dict(candidates[best_idx])
                best_cand["rerank_score"] = float(results[0].get("score", 0.0))
                reranked.append(best_cand)

        logger.debug(
            "TEI reranked %d candidates -> %d results (top_k=%d)",
            len(candidates),
            len(reranked),
            top_k,
        )
        return reranked[:top_k]

    except Exception as e:
        logger.warning(
            "TEI reranking call failed: %s. Falling back to original retrieval order.",
            e,
        )
        return candidates[:top_k]


async def health_check_tei_reranker(
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float = 5.0,
) -> bool:
    """Check availability of the TEI reranking service."""
    target_url = (base_url or settings.tei_base_url).rstrip("/")
    token = api_key or settings.tei_api_key

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    endpoints = [
        f"{target_url}/health/rerank",
        f"{target_url}/health",
        f"{target_url}/info",
    ]

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for ep in endpoints:
                try:
                    resp = await client.get(ep, headers=headers)
                    if resp.status_code == 200:
                        return True
                except httpx.HTTPError:
                    continue
        return False
    except Exception:
        return False


__all__ = [
    "extract_document_text",
    "rerank_documents_with_tei",
    "health_check_tei_reranker",
]

