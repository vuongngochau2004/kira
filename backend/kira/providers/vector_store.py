"""Qdrant vector store: client helpers and the QdrantVectorStore used by features."""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from kira.config import settings


@dataclass(frozen=True)
class VectorDocument:
    """Document to be stored in the vector store.

    Immutable data structure representing a chunk to be indexed.

    Attributes:
        id: Unique chunk identifier
        text: Text content of the chunk
        embedding: Dense vector representation
        metadata: Additional metadata (user_id, document_id, etc.)
    """

    id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    """Result from a vector similarity search.

    Attributes:
        id: Chunk identifier
        text: Text content of the retrieved chunk
        score: Cosine similarity score (0.0 - 1.0)
        metadata: Additional metadata from the stored document
    """

    id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


logger = logging.getLogger(__name__)


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

    for chunk, embedding in zip(chunks, embeddings, strict=False):
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
            f"avg: {sum(scores) / len(scores):.3f}"
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


class QdrantVectorStore:
    """Adapter that maps the vector store port to Qdrant."""

    async def search(
        self,
        embedding: list[float],
        k: int = 5,
        user_id: str | UUID | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Perform semantic similarity search in Qdrant.

        Args:
            embedding: Query vector
            k: Number of results
            user_id: Optional user filter for multi-tenant isolation
            min_score: Minimum similarity score

        Returns:
            List of SearchResult ordered by score descending
        """
        effective_min_score = min_score or settings.retrieval_min_score_threshold
        raw_results = search_similar(
            query_embedding=embedding,
            user_id=str(user_id) if user_id else None,
            limit=k,
            min_score=effective_min_score,
        )
        return [
            SearchResult(
                id=str(r.get("id", "")),
                text=r.get("text", ""),
                score=float(r.get("score", 0.0)),
                metadata={k: v for k, v in r.items() if k not in ("id", "text", "score")},
            )
            for r in raw_results
        ]

    async def upsert(self, documents: list[VectorDocument]) -> None:
        """Insert or update documents in Qdrant.

        Args:
            documents: List of VectorDocument to upsert
        """
        if not documents:
            return

        client = get_client()
        ensure_collection()

        points = [
            PointStruct(
                id=doc.id or str(uuid.uuid4()),
                vector=doc.embedding,
                payload={**doc.metadata, "text": doc.text},
            )
            for doc in documents
        ]

        client.upsert(
            collection_name=settings.qdrant_collection,
            points=points,
        )

    async def delete(self, document_ids: list[str]) -> None:
        """Delete vectors by source document IDs.

        Args:
            document_ids: List of source document IDs to delete
        """
        for doc_id in document_ids:
            delete_document(doc_id)

    async def delete_document(self, document_id: str | UUID) -> None:
        """Delete all vectors for a source document."""
        delete_document(document_id)

    async def health_check(self) -> bool:
        """Check Qdrant connectivity."""
        try:
            get_client().get_collections()
            return True
        except Exception:
            return False
