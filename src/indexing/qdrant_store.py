"""Qdrant vector storage wrapper."""

import sys
from pathlib import Path
from typing import Any
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    CreateCollection,
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
        chunk_id = f"{document_id}_chunk_{chunk.get('index', len(chunk_ids))}"

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
) -> list[dict]:
    """Search for similar chunks using vector similarity.

    Args:
        query_embedding: Query vector
        user_id: Optional user ID filter
        limit: Maximum number of results

    Returns:
        List of matching chunks with scores
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

    return [
        {
            "id": hit.id,
            "score": hit.score,
            "text": hit.payload.get("text", ""),
            "document_id": hit.payload.get("document_id"),
            "user_id": hit.payload.get("user_id"),
            "chunk_index": hit.payload.get("chunk_index"),
        }
        for hit in results
    ]


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
