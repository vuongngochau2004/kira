"""
Retrieval ABCs for document search.

This module defines Abstract Base Classes for retrieval operations,
enforcing pluggable retrieval strategies (dense, BM25, hybrid).

Retrieval Strategies:
- DenseRetrieverABC: Vector-based semantic search (Qdrant)
- BM25RetrieverABC: Keyword-based search (BM25)
- HybridRetrieverABC: Combined dense + BM25 with RRF fusion

Example:
    >>> from src.abc.retrieval import RetrieverABC, Document
    >>>
    >>> class MyRetriever(RetrieverABC):
    ...     async def retrieve(self, query: str, user_id: str, top_k: int = 5) -> list[Document]:
    ...         # Custom retrieval logic
    ...         return [Document(content="...", filename="doc.pdf")]
    ...
    ...     def get_stats(self) -> dict[str, Any]:
    ...         return {"total_docs": 100}
    ...
    ...     async def health_check(self) -> bool:
    ...         return True
"""

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Document:
    """
    Retrieved document chunk.

    Attributes:
        content: Document text content
        filename: Source filename
        page: Page number (if applicable)
        chunk_id: Unique chunk identifier
        score: Relevance score (from retrieval)
        metadata: Additional metadata (embedding_id, chunk_index, etc.)

    Example:
        >>> doc = Document(
        ...     content="Contract clause 1.1...",
        ...     filename="contract.pdf",
        ...     page=1,
        ...     chunk_id="chunk_123",
        ...     score=0.95
        ... )
    """

    content: str
    filename: str
    page: int | None = None
    chunk_id: str | None = None
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "filename": self.filename,
            "page": self.page,
            "chunk_id": self.chunk_id,
            "score": self.score,
            "metadata": self.metadata,
        }

    def get_excerpt(self, max_length: int = 200) -> str:
        """Get excerpt of document content."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."


class RetrieverABC(ABC):
    """
    ABC for document retrieval.

    Implementations can use vector search (Qdrant), BM25, or hybrid retrieval.

    All retrieval operations should be user-scoped for multi-tenancy.

    Subclasses:
        DenseRetrieverABC: Vector-based retrieval
        BM25RetrieverABC: Keyword-based retrieval
        HybridRetrieverABC: Combined retrieval with RRF

    Example:
        >>> class HybridRetriever(RetrieverABC):
        ...     def __init__(self, dense_retriever, bm25_retriever):
        ...         self.dense = dense_retriever
        ...         self.bm25 = bm25_retriever
        ...
        ...     async def retrieve(self, query: str, user_id: str, top_k: int = 5) -> list[Document]:
        ...         dense_docs = await self.dense.retrieve(query, user_id, top_k)
        ...         bm25_docs = await self.bm25.retrieve(query, user_id, top_k)
        ...         return self._rrf_fusion(dense_docs, bm25_docs, top_k)
        ...
        ...     def get_stats(self) -> dict[str, Any]:
        ...         return {"total_docs": 100}
        ...
        ...     async def health_check(self) -> bool:
        ...         return True
    """

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None
    ) -> list[Document]:
        """
        Retrieve documents for the query.

        Args:
            query: User query string
            user_id: User ID for user-scoped retrieval
            top_k: Number of documents to retrieve
            filters: Optional filters (document type, date range, etc.)

        Returns:
            List of retrieved documents, ranked by relevance

        Raises:
            ValueError: If query is empty or top_k <= 0
            Exception: If retrieval fails

        Example:
            >>> docs = await retriever.retrieve("hỏi về hợp đồng", "user123", top_k=5)
            >>> assert len(docs) <= 5
            >>> assert all(doc.score >= 0 for doc in docs)
        """
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """
        Get retrieval statistics.

        Returns:
            Dict with stats: total_docs, avg_latency, cache_hit_rate, etc.

        Example:
            >>> stats = retriever.get_stats()
            >>> print(f"Total documents: {stats['total_docs']}")
            >>> print(f"Average latency: {stats['avg_latency_ms']}ms")
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if retriever is healthy.

        Returns:
            True if retriever is operational, False otherwise

        Example:
            >>> if await retriever.health_check():
            ...     print("Retriever is healthy")
        """
        ...


class DenseRetrieverABC(RetrieverABC):
    """
    ABC for dense (vector-based) retrieval.

    Extends RetrieverABC with vector-based search capabilities.

    Uses semantic search with embeddings.

    Example:
        >>> class QdrantRetriever(DenseRetrieverABC):
        ...     async def retrieve(self, query: str, user_id: str, top_k: int = 5) -> list[Document]:
        ...         query_vector = await self.embedding_service.embed(query)
        ...         results = await self.qdrant_client.search(
        ...             collection_name=f"user_{user_id}",
        ...             query_vector=query_vector,
        ...             limit=top_k
        ...         )
        ...         return [self._to_document(r) for r in results]
        ...
        ...     async def retrieve_by_vector(self, query_vector: list[float], user_id: str, top_k: int = 5) -> list[Document]:
        ...         results = await self.qdrant_client.search(
        ...             collection_name=f"user_{user_id}",
        ...             query_vector=query_vector,
        ...             limit=top_k
        ...         )
        ...         return [self._to_document(r) for r in results]
        ...
        ...     def get_stats(self) -> dict[str, Any]:
        ...         return {"total_docs": 100}
        ...
        ...     async def health_check(self) -> bool:
        ...         return await self.qdrant_client.health_check()
    """

    @abstractmethod
    async def retrieve_by_vector(
        self,
        query_vector: list[float],
        user_id: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None
    ) -> list[Document]:
        """
        Retrieve documents by query vector.

        Args:
            query_vector: Query embedding vector
            user_id: User ID for user-scoped retrieval
            top_k: Number of documents to retrieve
            filters: Optional filters

        Returns:
            List of retrieved documents

        Example:
            >>> vector = await embedding_service.embed("query text")
            >>> docs = await retriever.retrieve_by_vector(vector, "user123", top_k=5)
        """
        ...


class BM25RetrieverABC(RetrieverABC):
    """
    ABC for BM25 (keyword-based) retrieval.

    Extends RetrieverABC with BM25 index management.

    Uses keyword matching and TF-IDF scoring.

    Example:
        >>> class MyBM25Retriever(BM25RetrieverABC):
        ...     def __init__(self, bm25_index):
        ...         self.index = bm25_index
        ...
        ...     async def retrieve(self, query: str, user_id: str, top_k: int = 5) -> list[Document]:
        ...         results = self.index.search(query, user_id, k=top_k)
        ...         return [Document(content=r.text, score=r.score) for r in results]
        ...
        ...     async def index_document(self, document: Document, user_id: str) -> None:
        ...         self.index.add(document, user_id)
        ...
        ...     async def remove_document(self, chunk_id: str, user_id: str) -> None:
        ...         self.index.remove(chunk_id, user_id)
        ...
        ...     async def bulk_index(self, documents: list[Document], user_id: str) -> None:
        ...         self.index.bulk_add(documents, user_id)
        ...
        ...     def get_stats(self) -> dict[str, Any]:
        ...         return {"total_docs": self.index.count(user_id)}
        ...
        ...     async def health_check(self) -> bool:
        ...         return self.index.is_healthy()
    """

    @abstractmethod
    async def index_document(
        self,
        document: Document,
        user_id: str
    ) -> None:
        """
        Index a document for BM25 retrieval.

        Args:
            document: Document to index
            user_id: User ID for user-scoped indexing

        Example:
            >>> doc = Document(content="...", filename="contract.pdf")
            >>> await retriever.index_document(doc, "user123")
        """
        ...

    @abstractmethod
    async def remove_document(
        self,
        chunk_id: str,
        user_id: str
    ) -> None:
        """
        Remove a document from BM25 index.

        Args:
            chunk_id: Chunk identifier to remove
            user_id: User ID for user-scoped removal

        Example:
            >>> await retriever.remove_document("chunk_123", "user123")
        """
        ...

    @abstractmethod
    async def bulk_index(
        self,
        documents: list[Document],
        user_id: str
    ) -> None:
        """
        Bulk index multiple documents.

        Args:
            documents: List of documents to index
            user_id: User ID for user-scoped indexing

        Example:
            >>> docs = [Document(content="...", filename=f"doc{i}.pdf") for i in range(100)]
            >>> await retriever.bulk_index(docs, "user123")
        """
        ...


class HybridRetrieverABC(RetrieverABC):
    """
    ABC for hybrid retrieval (dense + BM25 fusion).

    Extends RetrieverABC with RRF fusion capabilities.

    Uses Reciprocal Rank Fusion (RRF) to merge results.

    Example:
        >>> class MyHybridRetriever(HybridRetrieverABC):
        ...     def __init__(self, dense_retriever, bm25_retriever, rrf_k=60):
        ...         self.dense = dense_retriever
        ...         self.bm25 = bm25_retriever
        ...         self.rrf_k = rrf_k
        ...
        ...     async def retrieve(self, query: str, user_id: str, top_k: int = 5) -> list[Document]:
        ...         dense_docs = await self.dense.retrieve(query, user_id, top_k * 2)
        ...         bm25_docs = await self.bm25.retrieve(query, user_id, top_k * 2)
        ...         return self._rrf_fusion(dense_docs, bm25_docs, top_k)
        ...
        ...     async def retrieve_with_scores(self, query: str, user_id: str, top_k: int = 5) -> tuple[list[Document], dict[str, float]]:
        ...         dense_docs = await self.dense.retrieve(query, user_id, top_k * 2)
        ...         bm25_docs = await self.bm25.retrieve(query, user_id, top_k * 2)
        ...         fused_docs = self._rrf_fusion(dense_docs, bm25_docs, top_k)
        ...         scores = {doc.chunk_id: doc.score for doc in fused_docs}
        ...         return fused_docs, scores
        ...
        ...     def get_rrf_k(self) -> int:
        ...         return self.rrf_k
        ...
        ...     def get_stats(self) -> dict[str, Any]:
        ...         return {"rrf_k": self.rrf_k}
        ...
        ...     async def health_check(self) -> bool:
        ...         return await self.dense.health_check() and await self.bm25.health_check()
    """

    @abstractmethod
    async def retrieve_with_scores(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        dense_weight: float = 0.5,
        bm25_weight: float = 0.5
    ) -> tuple[list[Document], dict[str, float]]:
        """
        Retrieve with hybrid scoring and return individual strategy scores.

        Args:
            query: User query string
            user_id: User ID for user-scoped retrieval
            top_k: Number of documents to retrieve
            dense_weight: Weight for dense retrieval (0.0 to 1.0)
            bm25_weight: Weight for BM25 retrieval (0.0 to 1.0)

        Returns:
            Tuple of (documents, chunk_id_to_score_map)

        Example:
            >>> docs, scores = await retriever.retrieve_with_scores("query", "user123", top_k=5)
            >>> for doc in docs:
            ...     print(f"{doc.filename}: {scores[doc.chunk_id]}")
        """
        ...

    @abstractmethod
    def get_rrf_k(self) -> int:
        """
        Get RRF constant k.

        Returns:
            RRF k constant (typically 60)

        Example:
            >>> k = retriever.get_rrf_k()
            >>> print(f"RRF k constant: {k}")
        """
        ...
