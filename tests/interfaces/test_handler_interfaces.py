"""
Tests for handler interfaces.

Validates QueryHandlerBase ABC compliance and data models (HandlerResult, Citation, HandlerConfig).
"""

import pytest
from uuid import uuid4
from abc import ABC

from interfaces.handlers import (
    QueryHandlerBase,
    HandlerResult,
    HandlerConfig,
    Citation,
)
from interfaces.retrieval import Document, RetrieverBase
from interfaces.classification import ClassificationResult, Intent


# ============================================================================
# Mock Implementations
# ============================================================================

class MockQueryHandler(QueryHandlerBase):
    """Mock handler for testing ABC compliance."""

    def __init__(self, config: HandlerConfig | None = None):
        self.config = config or HandlerConfig()
        self.name = "MockHandler"

    async def handle(
        self,
        query: str,
        user_id: str,
        classification: ClassificationResult,
        context: dict | None = None
    ) -> HandlerResult:
        """Mock handle implementation."""
        return HandlerResult(
            content=f"Mock response for: {query}",
            metadata={"handler": self.name}
        )

    async def handle_stream(
        self,
        query: str,
        user_id: str,
        classification: ClassificationResult,
        context: dict | None = None
    ):
        """Mock handle_stream implementation."""
        yield {"type": "content", "data": {"text": f"Mock stream for: {query}"}}
        yield {"type": "done"}

    def can_handle(self, classification: ClassificationResult) -> bool:
        """Mock can_handle implementation."""
        return classification.intent == Intent.RAG

    def get_config(self) -> HandlerConfig:
        """Mock get_config implementation."""
        return self.config

    def get_name(self) -> str:
        """Mock get_name implementation."""
        return self.name


class MockDocument:
    """Mock implementation of Document protocol."""

    def __init__(self, content: str, filename: str, page: int | None = None):
        self._content = content
        self._filename = filename
        self._page = page
        self._metadata = {}

    @property
    def content(self) -> str:
        return self._content

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def page(self) -> int | None:
        return self._page

    @property
    def metadata(self) -> dict:
        return self._metadata

    def to_dict(self) -> dict:
        return {
            "content": self._content,
            "filename": self._filename,
            "page": self._page,
            "metadata": self._metadata,
        }


class MockRetriever:
    """Mock implementation of Retriever protocol."""

    def __init__(self):
        self.stats = {"total_docs": 100, "avg_latency_ms": 50.0}

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        filters: dict | None = None
    ) -> list:
        return [
            MockDocument(f"Content {i}", f"doc{i}.pdf", page=i + 1)
            for i in range(min(top_k, 3))
        ]

    def get_stats(self) -> dict:
        return self.stats

    async def health_check(self) -> bool:
        return True


# ============================================================================
# ABC Compliance Tests
# ============================================================================

def test_abc_is_abstract():
    """Test that QueryHandlerBase is an abstract base class."""
    assert issubclass(QueryHandlerBase, ABC)

    # Should not be able to instantiate ABC directly
    with pytest.raises(TypeError):
        QueryHandlerBase()


def test_mock_handler_is_instance():
    """Test that mock handler is instance of QueryHandlerBase."""
    handler = MockQueryHandler()
    assert isinstance(handler, QueryHandlerBase)


def test_mock_handler_has_all_methods():
    """Test that mock handler implements all required methods."""
    handler = MockQueryHandler()

    # Check all abstract methods are implemented
    assert hasattr(handler, 'handle')
    assert hasattr(handler, 'handle_stream')
    assert hasattr(handler, 'can_handle')
    assert hasattr(handler, 'get_config')
    assert hasattr(handler, 'get_name')

    # Check methods are callable
    assert callable(handler.handle)
    assert callable(handler.handle_stream)
    assert callable(handler.can_handle)
    assert callable(handler.get_config)
    assert callable(handler.get_name)


@pytest.mark.asyncio
async def test_mock_handler_methods_work():
    """Test that mock handler methods work correctly."""
    handler = MockQueryHandler()
    classification = ClassificationResult(
        intent=Intent.RAG,
        confidence=0.9,
        reason="Test classification"
    )

    # Test handle
    result = await handler.handle("test query", "user123", classification)
    assert result.content == "Mock response for: test query"
    assert result.metadata["handler"] == "MockHandler"
    assert result.is_success()

    # Test handle_stream
    chunks = []
    async for chunk in handler.handle_stream("test query", "user123", classification):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert chunks[0]["type"] == "content"
    assert chunks[1]["type"] == "done"

    # Test can_handle
    assert handler.can_handle(classification) is True

    # Test get_config
    config = handler.get_config()
    assert isinstance(config, HandlerConfig)

    # Test get_name
    assert handler.get_name() == "MockHandler"


def test_handler_has_correct_abstract_methods():
    """Test that QueryHandlerBase has correct abstract methods."""
    abstract_methods = []
    for name in dir(QueryHandlerBase):
        if not name.startswith('_'):
            attr = getattr(QueryHandlerBase, name)
            if getattr(attr, '__isabstractmethod__', False):
                abstract_methods.append(name)

    expected_abstracts = {
        'handle',
        'handle_stream',
        'can_handle',
        'get_config',
        'get_name'
    }

    assert set(abstract_methods) == expected_abstracts, \
        f"Abstract methods mismatch. Expected: {expected_abstracts}, Got: {set(abstract_methods)}"


# ============================================================================
# Data Model Tests
# ============================================================================

@pytest.mark.asyncio
async def test_citation_creation():
    """Test Citation creation."""
    citation = Citation(
        filename="contract.pdf",
        page=1,
        text="Contract clause 1.1...",
        confidence=0.95
    )

    assert citation.filename == "contract.pdf"
    assert citation.page == 1
    assert citation.text == "Contract clause 1.1..."
    assert citation.confidence == 0.95


@pytest.mark.asyncio
async def test_citation_to_dict():
    """Test Citation serialization."""
    citation = Citation(
        filename="contract.pdf",
        page=1,
        text="Contract clause 1.1...",
        url="https://example.com/contract.pdf",
        confidence=0.95
    )

    data = citation.to_dict()

    assert data["filename"] == "contract.pdf"
    assert data["page"] == 1
    assert data["text"] == "Contract clause 1.1..."
    assert data["url"] == "https://example.com/contract.pdf"
    assert data["confidence"] == 0.95


@pytest.mark.asyncio
async def test_handler_result_creation():
    """Test HandlerResult creation."""
    result = HandlerResult(
        content="Test response",
        citations=[Citation(filename="doc.pdf", text="...")],
        metadata={"handler": "TestHandler", "latency_ms": 1234}
    )

    assert result.content == "Test response"
    assert len(result.citations) == 1
    assert result.metadata["handler"] == "TestHandler"
    assert result.metadata["latency_ms"] == 1234


@pytest.mark.asyncio
async def test_handler_result_validation():
    """Test HandlerResult validation."""
    # Error status requires error message
    with pytest.raises(ValueError, match="Error status requires error message"):
        HandlerResult(content="...", status="error", error=None)


@pytest.mark.asyncio
async def test_handler_result_methods():
    """Test HandlerResult helper methods."""
    # Success result
    result = HandlerResult(content="Response")
    assert result.is_success()
    assert not result.is_error()

    # Error result
    result = HandlerResult(content="", status="error", error="Failed")
    assert result.is_error()
    assert not result.is_success()


@pytest.mark.asyncio
async def test_handler_result_get_latency():
    """Test HandlerResult.get_latency_ms()."""
    result = HandlerResult(
        content="Response",
        metadata={"latency_ms": 1234}
    )

    assert result.get_latency_ms() == 1234

    # No latency in metadata
    result = HandlerResult(content="Response")
    assert result.get_latency_ms() is None


@pytest.mark.asyncio
async def test_handler_result_to_dict():
    """Test HandlerResult serialization."""
    result = HandlerResult(
        content="Response",
        citations=[Citation(filename="doc.pdf", text="...")],
        metadata={"handler": "TestHandler"},
        conversation_id="conv_123",
        message_id="msg_456"
    )

    data = result.to_dict()

    assert data["content"] == "Response"
    assert len(data["citations"]) == 1
    assert data["metadata"]["handler"] == "TestHandler"
    assert data["conversation_id"] == "conv_123"
    assert data["message_id"] == "msg_456"
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_handler_result_frozen():
    """Test that HandlerResult is immutable."""
    result = HandlerResult(content="Response")

    with pytest.raises(Exception):  # FrozenInstanceError
        result.content = "Updated"


@pytest.mark.asyncio
async def test_handler_config_creation():
    """Test HandlerConfig creation with defaults."""
    config = HandlerConfig()

    assert config.max_retrieved_docs == 5
    assert config.max_tokens == 2000
    assert config.temperature == 0.7
    assert config.streaming_enabled is True
    assert config.timeout_ms == 30000
    assert config.retry_count == 2


@pytest.mark.asyncio
async def test_handler_config_custom():
    """Test HandlerConfig with custom values."""
    config = HandlerConfig(
        max_retrieved_docs=10,
        max_tokens=4000,
        temperature=0.5,
        streaming_enabled=False
    )

    assert config.max_retrieved_docs == 10
    assert config.max_tokens == 4000
    assert config.temperature == 0.5
    assert config.streaming_enabled is False


@pytest.mark.asyncio
async def test_handler_config_to_dict():
    """Test HandlerConfig serialization."""
    config = HandlerConfig(
        max_retrieved_docs=10,
        metadata={"custom": "value"}
    )

    data = config.to_dict()

    assert data["max_retrieved_docs"] == 10
    assert data["max_tokens"] == 2000
    assert data["temperature"] == 0.7
    assert data["metadata"]["custom"] == "value"


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_query_handler_with_uuid():
    """Test QueryHandler with UUID user_id."""
    handler = MockQueryHandler()
    user_id = uuid4()
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    result = await handler.handle("test query", str(user_id), classification)

    assert result.is_success()


@pytest.mark.asyncio
async def test_query_handler_with_context():
    """Test QueryHandler with context parameter."""
    handler = MockQueryHandler()
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)
    context = {"conversation_history": []}

    result = await handler.handle("test query", "user123", classification, context)

    assert result.is_success()


@pytest.mark.asyncio
async def test_retriever_with_filters():
    """Test Retriever with filters parameter."""
    retriever = MockRetriever()
    filters = {"document_type": "pdf"}

    docs = await retriever.retrieve("test query", "user123", top_k=3, filters=filters)

    assert len(docs) == 3


@pytest.mark.asyncio
async def test_citation_with_metadata():
    """Test Citation with metadata field."""
    citation = Citation(
        filename="doc.pdf",
        text="...",
        metadata={"chunk_id": "123", "embedding_id": "456"}
    )

    assert citation.metadata["chunk_id"] == "123"

    data = citation.to_dict()
    assert data["metadata"]["chunk_id"] == "123"
