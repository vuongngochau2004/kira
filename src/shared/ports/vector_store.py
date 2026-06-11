"""Port: Vector store contract.

Application core depends on this ABC, NOT on Qdrant directly.
Allows swapping Qdrant ↔ Weaviate ↔ Pinecone ↔ Chroma
without changing business logic.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


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


class VectorStorePort(ABC):
    """Port: what the application needs from any vector store.

    Example:
        >>> class MyVectorStore(VectorStorePort):
        ...     async def search(self, embedding, k=5, **kwargs):
        ...         return [SearchResult(id="1", text="...", score=0.9)]
    """

    @abstractmethod
    async def search(
        self,
        embedding: list[float],
        k: int = 5,
        user_id: str | UUID | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Perform semantic similarity search.

        Args:
            embedding: Query vector
            k: Number of results to return
            user_id: Optional user filter for multi-tenant isolation
            min_score: Minimum similarity score threshold

        Returns:
            List of SearchResult ordered by score descending
        """
        ...

    @abstractmethod
    async def upsert(self, documents: list[VectorDocument]) -> None:
        """Insert or update documents in the vector store.

        Args:
            documents: List of documents to upsert
        """
        ...

    @abstractmethod
    async def delete(self, document_ids: list[str]) -> None:
        """Delete documents by their IDs.

        Args:
            document_ids: List of chunk IDs to delete
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if vector store is reachable and operational.

        Returns:
            True if healthy, False otherwise
        """
        ...
