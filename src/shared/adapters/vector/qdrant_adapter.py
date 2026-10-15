"""Qdrant adapter for VectorStorePort."""

import uuid
from uuid import UUID

from qdrant_client.models import PointStruct

from src.config.config import settings
from src.modules.retrieval.infrastructure.vector import qdrant_store
from src.shared.ports.vector_store import SearchResult, VectorDocument, VectorStorePort


class QdrantAdapter(VectorStorePort):
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
        raw_results = qdrant_store.search_similar(
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

        client = qdrant_store.get_client()
        qdrant_store.ensure_collection()

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
            qdrant_store.delete_document(doc_id)

    async def delete_document(self, document_id: str | UUID) -> None:
        """Delete all vectors for a source document."""
        qdrant_store.delete_document(document_id)

    async def health_check(self) -> bool:
        """Check Qdrant connectivity."""
        try:
            qdrant_store.get_client().get_collections()
            return True
        except Exception:
            return False
