"""
Tests for RAGHandler.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.handlers.rag import RAGHandler
from src.interfaces.classification import ClassificationResult, Intent


@pytest.mark.asyncio
async def test_rag_handler_creation():
    """Test RAGHandler creation."""
    handler = RAGHandler()

    assert handler.get_name() == "RAGHandler"
    assert isinstance(handler.get_config(), object)


@pytest.mark.asyncio
async def test_rag_handler_can_handle():
    """Test RAGHandler.can_handle() method."""
    handler = RAGHandler()

    # RAG intent
    rag_classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)
    assert handler.can_handle(rag_classification)

    # CONVERSATIONAL intent
    conv_classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)
    assert not handler.can_handle(conv_classification)


@pytest.mark.asyncio
async def test_rag_handler_handle_with_wrong_intent():
    """Test RAGHandler with wrong intent raises error."""
    handler = RAGHandler()

    conv_classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)

    with pytest.raises(ValueError, match="cannot handle intent"):
        await handler.handle("query", "user123", conv_classification)


@pytest.mark.asyncio
async def test_rag_handler_handle_success():
    """Test RAGHandler successful execution."""
    # Mock RAG agent
    mock_rag_agent = AsyncMock()
    mock_rag_agent.query = AsyncMock(return_value={
        "content": "Test response",
        "citations": [
            {"filename": "test.pdf", "text": "Test citation", "page": 1}
        ],
        "total_docs": 5,
        "retrieval_history": []
    })

    handler = RAGHandler(rag_agent=mock_rag_agent)
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    result = await handler.handle("test query", "user123", classification)

    assert result.is_success()
    assert result.content == "Test response"
    assert len(result.citations) == 1
    assert result.citations[0].filename == "test.pdf"
    assert result.metadata["handler"] == "RAGHandler"
    assert result.metadata["docs_retrieved"] == 5


@pytest.mark.asyncio
async def test_rag_handler_handle_with_context():
    """Test RAGHandler with conversation history context."""
    mock_rag_agent = AsyncMock()
    mock_rag_agent.query = AsyncMock(return_value={
        "content": "Response with context",
        "citations": [],
        "total_docs": 0,
    })

    handler = RAGHandler(rag_agent=mock_rag_agent)
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    context = {"conversation_history": [{"role": "user", "content": "Previous query"}]}
    result = await handler.handle("new query", "user123", classification, context)

    assert result.is_success()
    assert result.content == "Response with context"


@pytest.mark.asyncio
async def test_rag_handler_handle_error():
    """Test RAGHandler error handling."""
    # Mock RAG agent that raises exception
    mock_rag_agent = AsyncMock()
    mock_rag_agent.query = AsyncMock(side_effect=Exception("RAG error"))

    handler = RAGHandler(rag_agent=mock_rag_agent)
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    result = await handler.handle("test query", "user123", classification)

    assert result.is_error()
    assert "RAG error" in result.error
    assert result.metadata["handler"] == "RAGHandler"


@pytest.mark.asyncio
async def test_rag_handler_stream():
    """Test RAGHandler streaming."""
    # Mock streaming response
    async def mock_stream(query, user_id, conversation_history=None, **kwargs):
        yield {"type": "retrieval", "data": {"iteration": 1, "docs_retrieved": 5}}
        yield {"type": "content", "data": {"text": "Response chunk"}}
        yield {"type": "metadata", "data": {"status": "success"}}

    mock_rag_agent = AsyncMock()
    mock_rag_agent.query_stream = mock_stream

    handler = RAGHandler(rag_agent=mock_rag_agent)
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    chunks = []
    async for chunk in handler.handle_stream("test query", "user123", classification):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0]["type"] == "retrieval"
    assert chunks[1]["type"] == "content"
    assert chunks[2]["type"] == "metadata"


@pytest.mark.asyncio
async def test_rag_handler_stream_with_wrong_intent():
    """Test RAGHandler streaming with wrong intent."""
    handler = RAGHandler()
    conv_classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)

    chunks = []
    async for chunk in handler.handle_stream("query", "user123", conv_classification):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0]["type"] == "metadata"
    assert chunks[0]["data"]["status"] == "error"


@pytest.mark.asyncio
async def test_rag_handler_stream_error():
    """Test RAGHandler streaming error handling."""
    mock_rag_agent = AsyncMock()

    async def mock_stream():
        yield {"type": "content", "data": {"text": "Chunk"}}
        raise Exception("Stream error")

    mock_rag_agent.query_stream = mock_stream

    handler = RAGHandler(rag_agent=mock_rag_agent)
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    chunks = []
    async for chunk in handler.handle_stream("query", "user123", classification):
        chunks.append(chunk)

    # Should get content chunk then error metadata
    assert len(chunks) >= 1
    assert any(c.get("type") == "metadata" and c.get("data", {}).get("status") == "error" for c in chunks)


@pytest.mark.asyncio
async def test_rag_handler_custom_config():
    """Test RAGHandler with custom config."""
    from src.interfaces.handlers import HandlerConfig

    config = HandlerConfig(max_retrieved_docs=10, max_tokens=4000)
    handler = RAGHandler(config=config)

    assert handler.config.max_retrieved_docs == 10
    assert handler.config.max_tokens == 4000


@pytest.mark.asyncio
async def test_rag_handler_citation_conversion():
    """Test citation format conversion."""
    mock_rag_agent = AsyncMock()
    mock_rag_agent.query = AsyncMock(return_value={
        "content": "Response",
        "citations": [
            {"filename": "doc1.pdf", "text": "Citation 1", "page": 1, "confidence": 0.9},
            {"filename": "doc2.pdf", "text": "Citation 2", "page": 2, "confidence": 0.8},
        ],
        "total_docs": 2,
    })

    handler = RAGHandler(rag_agent=mock_rag_agent)
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    result = await handler.handle("query", "user123", classification)

    assert len(result.citations) == 2
    assert result.citations[0].filename == "doc1.pdf"
    assert result.citations[0].confidence == 0.9
    assert result.citations[1].page == 2
