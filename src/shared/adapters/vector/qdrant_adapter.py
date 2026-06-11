"""Qdrant Adapter — implements VectorStorePort using existing qdrant_store.

This adapter wraps the qdrant_store module functions to conform to
the VectorStorePort interface defined in shared/ports/vector_store.py.

To swap to Weaviate or Pinecone, create a new adapter implementing
the same VectorStorePort — no application code changes needed.
"""
from uuid import UUID

from src.shared.ports.vector_store import VectorStorePort, VectorDocument, SearchResult


class QdrantAdapter(VectorStorePort):
    """Adapter: wraps qdrant_store functions to conform to VectorStorePort.

    Example:
        >>> adapter = QdrantAdapter()
        >>> results = await adapter.search(embedding=[0.1, 0.2, ...], k=5)
    """

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
        from src.modules.retrieval.infrastructure.vector.qdrant_store import search_similar
        from src.config.config import settings

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
        from src.modules.retrieval.infrastructure.vector.qdrant_store import upsert_point

        for doc in documents:
            payload = {**doc.metadata, "text": doc.text}
            upsert_point(
                point_id=doc.id,
                vector=doc.embedding,
                payload=payload,
            )

    async def delete(self, document_ids: list[str]) -> None:
        """Delete documents from Qdrant by their IDs.

        Args:
            document_ids: List of chunk IDs to delete
        """
        from src.modules.retrieval.infrastructure.vector.qdrant_store import delete_by_document_id

        for doc_id in document_ids:
            delete_by_document_id(doc_id)

    async def health_check(self) -> bool:
        """Check Qdrant connectivity."""
        try:
            from src.modules.retrieval.infrastructure.vector.qdrant_store import get_client
            get_client().get_collections()
            return True
        except Exception:
            return False
