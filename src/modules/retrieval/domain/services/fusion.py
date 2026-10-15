"""Reciprocal Rank Fusion (RRF) algorithm for combining multi-source search results."""

from collections import defaultdict

DEFAULT_RRF_K = 60


def make_doc_key(item: dict) -> str:
    """Create unique key from document metadata."""
    doc_id = item.get("document_id") or item.get("metadata", {}).get("document_id", "")
    chunk_idx = item.get("chunk_index")
    if chunk_idx is None:
        chunk_idx = item.get("metadata", {}).get("chunk_index", "")
    return f"{doc_id}_{chunk_idx}"


def build_sorted_results(
    doc_map: dict[str, dict],
    scores: dict[str, float],
) -> list[dict]:
    """Build sorted results with RRF scores and standardized structure."""
    results = []
    for key, rrf_score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        doc = doc_map[key].copy()
        doc["rrf_score"] = rrf_score

        if "text" not in doc:
            doc["text"] = doc.get("content", "")
        if "content" not in doc:
            doc["content"] = doc.get("text", "")

        results.append(doc)
    return results


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
            key = make_doc_key(item)
            doc_map[key] = item
            scores[key] += 1 / (k + rank + 1)

    return build_sorted_results(doc_map, scores)


# Backward-compatible private aliases
_make_doc_key = make_doc_key
_build_sorted_results = build_sorted_results

__all__ = [
    "DEFAULT_RRF_K",
    "reciprocal_rank_fusion",
    "make_doc_key",
    "build_sorted_results",
    "_make_doc_key",
    "_build_sorted_results",
]
