"""
Tests for handler protocols.

Validates protocol compliance and HandlerResult/Citation behavior.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock

from src.protocols.handlers import (
    QueryHandler,
    HandlerResult,
    HandlerConfig,
    Citation,
    Document,
    Retriever
)
from src.protocols.classification import ClassificationResult, Intent


class MockQueryHandler:
    """Mock implementation of QueryHandler protocol."""

    def __init__(self, name: str = "MockHandler"):
        self.name = name
        self.config = HandlerConfig(max_retrieved_docs=5)

    async def handle(
        self,
        query: str,
        user_id: str,
        classification: ClassificationResult,
        context: dict | None = None
    ) -> HandlerResult:
        return HandlerResult(
            content="Mock response",
            citations=[],
            metadata={"handler": self.name}
        )

    async def handle_stream(
        self,
        query: str,
        user_id: str,
        classification: ClassificationResult,
        context: dict | None = None
    ):
        yield {"type": "content", "data": {"text": "Mock streaming"}}
        yield {"type": "done"}

    def can_handle(self, classification: ClassificationResult) -> bool:
        return classification.intent == Intent.RAG

    def get_config(self) -> HandlerConfig:
        return self.config

    def get_name(self) -> str:
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


@pytest.mark.asyncio
async def test_query_handler_protocol():
    """Test QueryHandler protocol compliance."""
    handler = MockQueryHandler("TestHandler")

    # Test handle method
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)
    result = await handler.handle("test query", "user123", classification)

    assert result.content == "Mock response"
    assert result.metadata["handler"] == "TestHandler"


@pytest.mark.asyncio
async def test_query_handler_streaming():
    """Test QueryHandler handle_stream method."""
    handler = MockQueryHandler()
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    chunks = []
    async for chunk in handler.handle_stream("test query", "user123", classification):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert chunks[0]["type"] == "content"
    assert chunks[1]["type"] == "done"


@pytest.mark.asyncio
async def test_query_handler_can_handle():
    """Test QueryHandler.can_handle() method."""
    handler = MockQueryHandler()

    # RAG intent
    rag_classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)
    assert handler.can_handle(rag_classification)

    # CONVERSATIONAL intent
    conv_classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)
    assert not handler.can_handle(conv_classification)


@pytest.mark.asyncio
async def test_query_handler_get_config():
    """Test QueryHandler.get_config() method."""
    handler = MockQueryHandler()
    config = handler.get_config()

    assert isinstance(config, HandlerConfig)
    assert config.max_retrieved_docs == 5


@pytest.mark.asyncio
async def test_query_handler_get_name():
    """Test QueryHandler.get_name() method."""
    handler = MockQueryHandler("CustomHandler")
    assert handler.get_name() == "CustomHandler"


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
async def test_document_protocol():
    """Test Document protocol compliance."""
    doc = MockDocument("Test content", "test.pdf", page=1)

    assert doc.content == "Test content"
    assert doc.filename == "test.pdf"
    assert doc.page == 1
    assert isinstance(doc.metadata, dict)

    data = doc.to_dict()
    assert data["content"] == "Test content"
    assert data["filename"] == "test.pdf"


@pytest.mark.asyncio
async def test_retriever_protocol():
    """Test Retriever protocol compliance."""
    retriever = MockRetriever()

    # Test retrieve method
    docs = await retriever.retrieve("test query", "user123", top_k=5)

    assert len(docs) == 3
    assert all(isinstance(doc, MockDocument) for doc in docs)

    # Test get_stats method
    stats = retriever.get_stats()
    assert stats["total_docs"] == 100
    assert stats["avg_latency_ms"] == 50.0

    # Test health_check method
    assert await retriever.health_check()


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
