"""
Tests for Retriever ABCs.

This test suite verifies:
- ABC compliance with @abstractmethod decorators
- Inheritance chain (Dense/BM25/Hybrid inherit from RetrieverABC)
- Protocol equivalence (ABC methods match Protocol methods)
- Mock implementations for testing
"""

import pytest
from abc import ABC
from typing import Any

from src.abc.retrieval import (
    RetrieverABC,
    DenseRetrieverABC,
    BM25RetrieverABC,
    HybridRetrieverABC,
    Document
)
from src.protocols.retrieval import (
    Retriever,
    DenseRetriever,
    BM25Retriever,
    HybridRetriever as ProtocolHybridRetriever
)


class TestDocument:
    """Test Document dataclass."""

    def test_document_creation(self):
        """Test creating a Document with all fields."""
        doc = Document(
            content="Test content",
            filename="test.pdf",
            page=1,
            chunk_id="chunk_123",
            score=0.95,
            metadata={"key": "value"}
        )

        assert doc.content == "Test content"
        assert doc.filename == "test.pdf"
        assert doc.page == 1
        assert doc.chunk_id == "chunk_123"
        assert doc.score == 0.95
        assert doc.metadata == {"key": "value"}

    def test_document_defaults(self):
        """Test creating a Document with default values."""
        doc = Document(
            content="Test content",
            filename="test.pdf"
        )

        assert doc.page is None
        assert doc.chunk_id is None
        assert doc.score == 0.0
        assert doc.metadata == {}

    def test_document_to_dict(self):
        """Test converting Document to dictionary."""
        doc = Document(
            content="Test",
            filename="test.pdf",
            page=1,
            chunk_id="chunk_1",
            score=0.9,
            metadata={"key": "value"}
        )

        expected = {
            "content": "Test",
            "filename": "test.pdf",
            "page": 1,
            "chunk_id": "chunk_1",
            "score": 0.9,
            "metadata": {"key": "value"}
        }

        assert doc.to_dict() == expected

    def test_document_get_excerpt(self):
        """Test getting document excerpt."""
        long_content = "a" * 300
        doc = Document(content=long_content, filename="test.pdf")

        excerpt = doc.get_excerpt(max_length=200)
        assert len(excerpt) == 203  # 200 + "..."
        assert excerpt.endswith("...")

    def test_document_get_excerpt_short(self):
        """Test getting excerpt when content is short."""
        short_content = "short content"
        doc = Document(content=short_content, filename="test.pdf")

        excerpt = doc.get_excerpt(max_length=200)
        assert excerpt == short_content


class TestRetrieverABC:
    """Test RetrieverABC abstract base class."""

    def test_retriever_abc_is_abstract(self):
        """Test that RetrieverABC cannot be instantiated."""
        with pytest.raises(TypeError):
            RetrieverABC()

    def test_retriever_abc_has_abstract_methods(self):
        """Test that RetrieverABC defines abstract methods."""
        abstract_methods = RetrieverABC.__abstractmethods__

        assert "retrieve" in abstract_methods
        assert "get_stats" in abstract_methods
        assert "health_check" in abstract_methods
        assert len(abstract_methods) == 3

    def test_retriever_abc_inherits_from_abc(self):
        """Test that RetrieverABC inherits from ABC."""
        assert issubclass(RetrieverABC, ABC)

    def test_retriever_abc_method_signatures(self):
        """Test that RetrieverABC methods have correct signatures."""
        import inspect

        # Check retrieve signature
        retrieve_sig = inspect.signature(RetrieverABC.retrieve)
        params = list(retrieve_sig.parameters.keys())
        assert "query" in params
        assert "user_id" in params
        assert "top_k" in params
        assert "filters" in params

        # Check get_stats signature (only self parameter)
        get_stats_sig = inspect.signature(RetrieverABC.get_stats)
        assert len(get_stats_sig.parameters) == 1  # Only self
        assert "self" in get_stats_sig.parameters

        # Check health_check signature (only self parameter)
        health_check_sig = inspect.signature(RetrieverABC.health_check)
        assert len(health_check_sig.parameters) == 1  # Only self
        assert "self" in health_check_sig.parameters


class MockRetriever(RetrieverABC):
    """Mock implementation of RetrieverABC for testing."""

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None
    ) -> list[Document]:
        return [Document(content="Test", filename="test.pdf", score=0.9)]

    def get_stats(self) -> dict[str, Any]:
        return {"total_docs": 100}

    async def health_check(self) -> bool:
        return True


class TestRetrieverImplementation:
    """Test that concrete implementations of RetrieverABC work correctly."""

    @pytest.mark.asyncio
    async def test_mock_retriever_can_be_instantiated(self):
        """Test that a concrete implementation can be instantiated."""
        retriever = MockRetriever()
        assert isinstance(retriever, RetrieverABC)

    @pytest.mark.asyncio
    async def test_mock_retriever_retrieve(self):
        """Test retrieve method."""
        retriever = MockRetriever()
        docs = await retriever.retrieve("query", "user123", top_k=5)

        assert len(docs) == 1
        assert docs[0].content == "Test"
        assert docs[0].filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_mock_retriever_get_stats(self):
        """Test get_stats method."""
        retriever = MockRetriever()
        stats = retriever.get_stats()

        assert stats == {"total_docs": 100}

    @pytest.mark.asyncio
    async def test_mock_retriever_health_check(self):
        """Test health_check method."""
        retriever = MockRetriever()
        is_healthy = await retriever.health_check()

        assert is_healthy is True


class TestDenseRetrieverABC:
    """Test DenseRetrieverABC abstract base class."""

    def test_dense_retriever_abc_inherits_from_retriever(self):
        """Test that DenseRetrieverABC inherits from RetrieverABC."""
        assert issubclass(DenseRetrieverABC, RetrieverABC)

    def test_dense_retriever_abc_is_abstract(self):
        """Test that DenseRetrieverABC cannot be instantiated."""
        with pytest.raises(TypeError):
            DenseRetrieverABC()

    def test_dense_retriever_abc_has_retrieve_by_vector(self):
        """Test that DenseRetrieverABC has retrieve_by_vector method."""
        assert "retrieve_by_vector" in DenseRetrieverABC.__abstractmethods__

    def test_dense_retriever_abc_total_abstract_methods(self):
        """Test total abstract methods count."""
        # Should have 3 from RetrieverABC + 1 from DenseRetrieverABC
        abstract_methods = DenseRetrieverABC.__abstractmethods__
        assert "retrieve" in abstract_methods
        assert "get_stats" in abstract_methods
        assert "health_check" in abstract_methods
        assert "retrieve_by_vector" in abstract_methods
        assert len(abstract_methods) == 4


class MockDenseRetriever(DenseRetrieverABC):
    """Mock implementation of DenseRetrieverABC for testing."""

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None
    ) -> list[Document]:
        return [Document(content="Dense result", filename="test.pdf", score=0.95)]

    async def retrieve_by_vector(
        self,
        query_vector: list[float],
        user_id: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None
    ) -> list[Document]:
        return [Document(content="Vector result", filename="test.pdf", score=0.9)]

    def get_stats(self) -> dict[str, Any]:
        return {"total_docs": 100, "type": "dense"}

    async def health_check(self) -> bool:
        return True


class TestDenseRetrieverImplementation:
    """Test that concrete implementations of DenseRetrieverABC work correctly."""

    @pytest.mark.asyncio
    async def test_mock_dense_retriever_can_be_instantiated(self):
        """Test that a concrete implementation can be instantiated."""
        retriever = MockDenseRetriever()
        assert isinstance(retriever, DenseRetrieverABC)
        assert isinstance(retriever, RetrieverABC)

    @pytest.mark.asyncio
    async def test_mock_dense_retriever_retrieve_by_vector(self):
        """Test retrieve_by_vector method."""
        retriever = MockDenseRetriever()
        docs = await retriever.retrieve_by_vector([0.1, 0.2, 0.3], "user123", top_k=5)

        assert len(docs) == 1
        assert docs[0].content == "Vector result"


class TestBM25RetrieverABC:
    """Test BM25RetrieverABC abstract base class."""

    def test_bm25_retriever_abc_inherits_from_retriever(self):
        """Test that BM25RetrieverABC inherits from RetrieverABC."""
        assert issubclass(BM25RetrieverABC, RetrieverABC)

    def test_bm25_retriever_abc_is_abstract(self):
        """Test that BM25RetrieverABC cannot be instantiated."""
        with pytest.raises(TypeError):
            BM25RetrieverABC()

    def test_bm25_retriever_abc_has_indexing_methods(self):
        """Test that BM25RetrieverABC has indexing methods."""
        abstract_methods = BM25RetrieverABC.__abstractmethods__
        assert "index_document" in abstract_methods
        assert "remove_document" in abstract_methods
        assert "bulk_index" in abstract_methods

    def test_bm25_retriever_abc_total_abstract_methods(self):
        """Test total abstract methods count."""
        # Should have 3 from RetrieverABC + 3 from BM25RetrieverABC
        abstract_methods = BM25RetrieverABC.__abstractmethods__
        assert "retrieve" in abstract_methods
        assert "get_stats" in abstract_methods
        assert "health_check" in abstract_methods
        assert "index_document" in abstract_methods
        assert "remove_document" in abstract_methods
        assert "bulk_index" in abstract_methods
        assert len(abstract_methods) == 6


class MockBM25Retriever(BM25RetrieverABC):
    """Mock implementation of BM25RetrieverABC for testing."""

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None
    ) -> list[Document]:
        return [Document(content="BM25 result", filename="test.pdf", score=0.85)]

    async def index_document(self, document: Document, user_id: str) -> None:
        pass  # Mock implementation

    async def remove_document(self, chunk_id: str, user_id: str) -> None:
        pass  # Mock implementation

    async def bulk_index(self, documents: list[Document], user_id: str) -> None:
        pass  # Mock implementation

    def get_stats(self) -> dict[str, Any]:
        return {"total_docs": 100, "type": "bm25"}

    async def health_check(self) -> bool:
        return True


class TestBM25RetrieverImplementation:
    """Test that concrete implementations of BM25RetrieverABC work correctly."""

    @pytest.mark.asyncio
    async def test_mock_bm25_retriever_can_be_instantiated(self):
        """Test that a concrete implementation can be instantiated."""
        retriever = MockBM25Retriever()
        assert isinstance(retriever, BM25RetrieverABC)
        assert isinstance(retriever, RetrieverABC)

    @pytest.mark.asyncio
    async def test_mock_bm25_retriever_index_document(self):
        """Test index_document method."""
        retriever = MockBM25Retriever()
        doc = Document(content="Test", filename="test.pdf")

        # Should not raise
        await retriever.index_document(doc, "user123")

    @pytest.mark.asyncio
    async def test_mock_bm25_retriever_remove_document(self):
        """Test remove_document method."""
        retriever = MockBM25Retriever()

        # Should not raise
        await retriever.remove_document("chunk_123", "user123")

    @pytest.mark.asyncio
    async def test_mock_bm25_retriever_bulk_index(self):
        """Test bulk_index method."""
        retriever = MockBM25Retriever()
        docs = [
            Document(content=f"Test {i}", filename=f"test{i}.pdf")
            for i in range(10)
        ]

        # Should not raise
        await retriever.bulk_index(docs, "user123")


class TestHybridRetrieverABC:
    """Test HybridRetrieverABC abstract base class."""

    def test_hybrid_retriever_abc_inherits_from_retriever(self):
        """Test that HybridRetrieverABC inherits from RetrieverABC."""
        assert issubclass(HybridRetrieverABC, RetrieverABC)

    def test_hybrid_retriever_abc_is_abstract(self):
        """Test that HybridRetrieverABC cannot be instantiated."""
        with pytest.raises(TypeError):
            HybridRetrieverABC()

    def test_hybrid_retriever_abc_has_hybrid_methods(self):
        """Test that HybridRetrieverABC has hybrid methods."""
        abstract_methods = HybridRetrieverABC.__abstractmethods__
        assert "retrieve_with_scores" in abstract_methods
        assert "get_rrf_k" in abstract_methods

    def test_hybrid_retriever_abc_total_abstract_methods(self):
        """Test total abstract methods count."""
        # Should have 3 from RetrieverABC + 2 from HybridRetrieverABC
        abstract_methods = HybridRetrieverABC.__abstractmethods__
        assert "retrieve" in abstract_methods
        assert "get_stats" in abstract_methods
        assert "health_check" in abstract_methods
        assert "retrieve_with_scores" in abstract_methods
        assert "get_rrf_k" in abstract_methods
        assert len(abstract_methods) == 5


class MockHybridRetriever(HybridRetrieverABC):
    """Mock implementation of HybridRetrieverABC for testing."""

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None
    ) -> list[Document]:
        return [Document(content="Hybrid result", filename="test.pdf", score=0.9)]

    async def retrieve_with_scores(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        dense_weight: float = 0.5,
        bm25_weight: float = 0.5
    ) -> tuple[list[Document], dict[str, float]]:
        docs = [Document(content=f"Result {i}", filename="test.pdf", score=0.9 - i * 0.1)
                for i in range(top_k)]
        scores = {f"chunk_{i}": 0.9 - i * 0.1 for i in range(top_k)}
        return docs, scores

    def get_rrf_k(self) -> int:
        return 60

    def get_stats(self) -> dict[str, Any]:
        return {"total_docs": 100, "type": "hybrid", "rrf_k": 60}

    async def health_check(self) -> bool:
        return True


class TestHybridRetrieverImplementation:
    """Test that concrete implementations of HybridRetrieverABC work correctly."""

    @pytest.mark.asyncio
    async def test_mock_hybrid_retriever_can_be_instantiated(self):
        """Test that a concrete implementation can be instantiated."""
        retriever = MockHybridRetriever()
        assert isinstance(retriever, HybridRetrieverABC)
        assert isinstance(retriever, RetrieverABC)

    @pytest.mark.asyncio
    async def test_mock_hybrid_retriever_retrieve_with_scores(self):
        """Test retrieve_with_scores method."""
        retriever = MockHybridRetriever()
        docs, scores = await retriever.retrieve_with_scores("query", "user123", top_k=3)

        assert len(docs) == 3
        assert len(scores) == 3
        assert "chunk_0" in scores
        assert scores["chunk_0"] == 0.9

    @pytest.mark.asyncio
    async def test_mock_hybrid_retriever_get_rrf_k(self):
        """Test get_rrf_k method."""
        retriever = MockHybridRetriever()
        rrf_k = retriever.get_rrf_k()

        assert rrf_k == 60


class TestProtocolEquivalence:
    """Test that ABCs match their corresponding Protocol interfaces."""

    def test_retriever_abc_matches_protocol_methods(self):
        """Test that RetrieverABC has same methods as Retriever Protocol."""
        abc_methods = {
            "retrieve", "get_stats", "health_check"
        }

        # Get protocol methods (excluding private/special)
        protocol_methods = {
            m for m in dir(Retriever)
            if not m.startswith('_') and callable(getattr(Retriever, m))
        }

        assert abc_methods == protocol_methods

    def test_dense_retriever_abc_matches_protocol_methods(self):
        """Test that DenseRetrieverABC has same methods as DenseRetriever Protocol."""
        abc_methods = {
            "retrieve", "get_stats", "health_check", "retrieve_by_vector"
        }

        protocol_methods = {
            m for m in dir(DenseRetriever)
            if not m.startswith('_') and callable(getattr(DenseRetriever, m))
        }

        assert abc_methods == protocol_methods

    def test_bm25_retriever_abc_matches_protocol_methods(self):
        """Test that BM25RetrieverABC has same methods as BM25Retriever Protocol."""
        abc_methods = {
            "retrieve", "get_stats", "health_check",
            "index_document", "remove_document", "bulk_index"
        }

        protocol_methods = {
            m for m in dir(BM25Retriever)
            if not m.startswith('_') and callable(getattr(BM25Retriever, m))
        }

        assert abc_methods == protocol_methods

    def test_hybrid_retriever_abc_matches_protocol_methods(self):
        """Test that HybridRetrieverABC has same methods as HybridRetriever Protocol."""
        abc_methods = {
            "retrieve", "get_stats", "health_check",
            "retrieve_with_scores", "get_rrf_k"
        }

        protocol_methods = {
            m for m in dir(ProtocolHybridRetriever)
            if not m.startswith('_') and callable(getattr(ProtocolHybridRetriever, m))
        }

        assert abc_methods == protocol_methods


class TestInheritanceChain:
    """Test inheritance chain of retriever ABCs."""

    def test_dense_retriever_inheritance(self):
        """Test DenseRetrieverABC inheritance chain."""
        assert issubclass(DenseRetrieverABC, RetrieverABC)
        assert issubclass(DenseRetrieverABC, ABC)

        # Test mock implementation
        assert isinstance(MockDenseRetriever(), DenseRetrieverABC)
        assert isinstance(MockDenseRetriever(), RetrieverABC)
        assert isinstance(MockDenseRetriever(), ABC)

    def test_bm25_retriever_inheritance(self):
        """Test BM25RetrieverABC inheritance chain."""
        assert issubclass(BM25RetrieverABC, RetrieverABC)
        assert issubclass(BM25RetrieverABC, ABC)

        # Test mock implementation
        assert isinstance(MockBM25Retriever(), BM25RetrieverABC)
        assert isinstance(MockBM25Retriever(), RetrieverABC)
        assert isinstance(MockBM25Retriever(), ABC)

    def test_hybrid_retriever_inheritance(self):
        """Test HybridRetrieverABC inheritance chain."""
        assert issubclass(HybridRetrieverABC, RetrieverABC)
        assert issubclass(HybridRetrieverABC, ABC)

        # Test mock implementation
        assert isinstance(MockHybridRetriever(), HybridRetrieverABC)
        assert isinstance(MockHybridRetriever(), RetrieverABC)
        assert isinstance(MockHybridRetriever(), ABC)
