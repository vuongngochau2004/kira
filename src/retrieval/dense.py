"""Dense/vector retrieval using Qdrant semantic similarity."""

import sys
from pathlib import Path
from typing import Any
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.indexing.qdrant_store import search_similar


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
        List of retrieved chunks with scores
    """
    return search_similar(
        query_embedding=query_embedding,
        user_id=user_id,
        limit=k,
    )


__all__ = ["dense_search"]
