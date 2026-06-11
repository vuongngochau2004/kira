"""Dense/vector retrieval using Qdrant semantic similarity."""

from uuid import UUID

from indexing.qdrant_store import search_similar
from config.config import settings


def dense_search(
    query_embedding: list[float],
    user_id: UUID | str | None = None,
    k: int = 5,
) -> list[dict]:
    """Perform dense vector similarity search.

    Args:
        query_embedding: Query vector
        user_id: Optional user ID filter
        k: Number of results to return

    Returns:
        List of retrieved chunks with standardized structure
    """
    results = search_similar(
        query_embedding=query_embedding,
        user_id=user_id,
        limit=k,
        min_score=settings.retrieval_min_score_threshold,
    )

    # Standardize structure: ensure all fields present
    return [
        {
            "id": r.get("id"),
            "text": r.get("text", ""),
            "content": r.get("text", ""),  # Alias for consistency
            "metadata": {
                "document_id": r.get("document_id"),
                "user_id": r.get("user_id"),
                "chunk_index": r.get("chunk_index"),
                "page_number": r.get("page_number"),
            },
            "document_id": r.get("document_id"),
            "chunk_index": r.get("chunk_index"),
            "page_number": r.get("page_number"),
            "score": r.get("score", 0.0),
        }
        for r in results
    ]


__all__ = ["dense_search"]
