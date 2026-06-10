"""Qdrant vector storage wrapper."""

import logging
import uuid
from uuid import UUID

from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)

from config.config import settings


# Singleton client
_qdrant_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    """Get Qdrant client singleton."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=60,
            prefer_grpc=False,
        )
    return _qdrant_client


def ensure_collection() -> None:
    """Ensure Qdrant collection exists."""
    client = get_client()
    try:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.qdrant_vector_dim,
                distance=Distance.COSINE,
            ),
        )
    except Exception:
        # Collection likely exists
        pass


def store_chunks(
    chunks: list[dict],
    embeddings: list[list[float]],
    document_id: UUID | str,
    user_id: UUID | str,
) -> list[str]:
    """Store document chunks with embeddings in Qdrant.

    Args:
        chunks: List of chunk dicts with index, content, metadata
        embeddings: List of embedding vectors
        document_id: Document ID
        user_id: User ID for filtering

    Returns:
        List of Qdrant point IDs
    """
    client = get_client()
    ensure_collection()

    points = []
    chunk_ids = []

    for chunk, embedding in zip(chunks, embeddings):
        name = f"{document_id}_chunk_{chunk.get('index', len(chunk_ids))}"
        chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, name))

        point = PointStruct(
            id=chunk_id,
            vector=embedding,
            payload={
                "text": chunk.get("content", ""),
                "document_id": str(document_id),
                "user_id": str(user_id),
                "chunk_index": chunk.get("index", len(chunk_ids)),
                **chunk.get("metadata", {}),
            },
        )
        points.append(point)
        chunk_ids.append(chunk_id)

    client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
    )

    return chunk_ids


def search_similar(
    query_embedding: list[float],
    user_id: UUID | str | None = None,
    limit: int = 5,
    min_score: float = 0.65,
) -> list[dict]:
    """Search for similar chunks using vector similarity.

    Args:
        query_embedding: Query vector
        user_id: Optional user ID filter
        limit: Maximum number of results
        min_score: Minimum similarity score threshold (0.0-1.0)

    Returns:
        List of matching chunks with scores (filtered by min_score)
    """
    client = get_client()
    ensure_collection()

    # Build filter
    query_filter = None
    if user_id is not None:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=str(user_id)),
                ),
            ],
        )

    results = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_embedding,
        limit=limit,
        query_filter=query_filter,
    ).points

    # ✅ Filter results by minimum score threshold
    # This prevents irrelevant documents from being retrieved
    filtered_results = [
        {
            "id": hit.id,
            "score": hit.score,
            "text": hit.payload.get("text", "") if hit.payload else "",
            "document_id": hit.payload.get("document_id") if hit.payload else None,
            "user_id": hit.payload.get("user_id") if hit.payload else None,
            "chunk_index": hit.payload.get("chunk_index") if hit.payload else None,
            "page_number": hit.payload.get("page_number") if hit.payload else None,
        }
        for hit in results
        if hit.score >= min_score
    ]

    # ✅ Log retrieval quality metrics for debugging
    if results:
        scores = [hit.score for hit in results]
        logger.debug(
            f"Qdrant retrieval: {len(filtered_results)}/{len(results)} results "
            f"passed score threshold (min={min_score:.2f}). "
            f"Score range: {min(scores):.3f} - {max(scores):.3f}, "
            f"avg: {sum(scores)/len(scores):.3f}"
        )
    else:
        logger.warning(f"Qdrant retrieval returned 0 results for user_id={user_id}")

    return filtered_results


def delete_document(document_id: UUID | str) -> None:
    """Delete all chunks for a document from Qdrant.

    Args:
        document_id: Document ID to delete
    """
    client = get_client()
    ensure_collection()

    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=str(document_id)),
                ),
            ],
        ),
    )


async def close() -> None:
    """Close Qdrant client connection."""
    global _qdrant_client
    if _qdrant_client is not None:
        # Qdrant client doesn't have explicit close method
        _qdrant_client = None


__all__ = [
    "get_client",
    "ensure_collection",
    "store_chunks",
    "search_similar",
    "delete_document",
    "close",
]
