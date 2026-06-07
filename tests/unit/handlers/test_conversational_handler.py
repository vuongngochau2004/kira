"""
Tests for ConversationalHandler.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.handlers.conversational import ConversationalHandler
from src.interfaces.classification import ClassificationResult, Intent


@pytest.mark.asyncio
async def test_conversational_handler_creation():
    """Test ConversationalHandler creation."""
    handler = ConversationalHandler()

    assert handler.get_name() == "ConversationalHandler"
    assert isinstance(handler.get_config(), object)


@pytest.mark.asyncio
async def test_conversational_handler_can_handle():
    """Test ConversationalHandler.can_handle() method."""
    handler = ConversationalHandler()

    # CONVERSATIONAL intent
    conv_classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)
    assert handler.can_handle(conv_classification)

    # RAG intent
    rag_classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)
    assert not handler.can_handle(rag_classification)


@pytest.mark.asyncio
async def test_conversational_handler_handle_with_wrong_intent():
    """Test ConversationalHandler with wrong intent raises error."""
    handler = ConversationalHandler()

    rag_classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    with pytest.raises(ValueError, match="cannot handle intent"):
        await handler.handle("query", "user123", rag_classification)


@pytest.mark.asyncio
@patch("src.handlers.conversational.chat_async")
async def test_conversational_handler_handle_success(mock_chat_async):
    """Test ConversationalHandler successful execution."""
    mock_chat_async.return_value = {"content": "Hello! How can I help you?"}

    handler = ConversationalHandler()
    classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)

    result = await handler.handle("xin chào", "user123", classification)

    assert result.is_success()
    assert result.content == "Hello! How can I help you?"
    assert len(result.citations) == 0  # No citations for conversational
    assert result.metadata["handler"] == "ConversationalHandler"


@pytest.mark.asyncio
@patch("src.handlers.conversational.chat_async")
async def test_conversational_handler_handle_with_context(mock_chat_async):
    """Test ConversationalHandler with conversation history."""
    mock_chat_async.return_value = {"content": "Nice to meet you again!"}

    handler = ConversationalHandler()
    classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)

    context = {"conversation_history": [{"role": "user", "content": "Previous message"}]}
    result = await handler.handle("nice to meet you", "user123", classification, context)

    assert result.is_success()
    assert "Nice to meet you again!" in result.content


@pytest.mark.asyncio
@patch("src.handlers.conversational.chat_async")
async def test_conversational_handler_handle_error(mock_chat_async):
    """Test ConversationalHandler error handling."""
    mock_chat_async.side_effect = Exception("LLM error")

    handler = ConversationalHandler(max_retries=1)
    classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)

    result = await handler.handle("test", "user123", classification)

    assert result.is_error()
    assert "không thể trả lời" in result.content
    assert "LLM error" in result.error


@pytest.mark.asyncio
@patch("src.handlers.conversational.chat_async_stream")
@patch("src.handlers.conversational.stream_with_thinking_separation")
async def test_conversational_handler_stream(mock_thinking, mock_chat_stream):
    """Test ConversationalHandler streaming."""
    # Mock streaming response
    async def mock_stream_gen():
        yield {"type": "content", "text": "Hello"}

    mock_chat_stream.return_value = mock_stream_gen()
    mock_thinking.return_value = [
        {"type": "content", "text": "Hello"}
    ]

    handler = ConversationalHandler()
    classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)

    chunks = []
    async for chunk in handler.handle_stream("xin chào", "user123", classification):
        chunks.append(chunk)

    assert len(chunks) >= 1  # At least content + metadata
    assert any(c["type"] == "content" for c in chunks)


@pytest.mark.asyncio
async def test_conversational_handler_stream_with_wrong_intent():
    """Test ConversationalHandler streaming with wrong intent."""
    handler = ConversationalHandler()
    rag_classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    chunks = []
    async for chunk in handler.handle_stream("query", "user123", rag_classification):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0]["type"] == "metadata"
    assert chunks[0]["data"]["status"] == "error"


@pytest.mark.asyncio
@patch("src.handlers.conversational.chat_async")
async def test_conversational_handler_custom_config(mock_chat_async):
    """Test ConversationalHandler with custom config."""
    from src.interfaces.handlers import HandlerConfig

    mock_chat_async.return_value = {"content": "Response"}

    config = HandlerConfig(temperature=0.5, max_tokens=1000)
    handler = ConversationalHandler(config=config)

    classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)
    await handler.handle("test", "user123", classification)

    # Verify temperature was passed correctly
    mock_chat_async.assert_called_once()
    call_kwargs = mock_chat_async.call_args[1]
    assert call_kwargs["temperature"] == 0.5
    assert call_kwargs["max_tokens"] == 1000


@pytest.mark.asyncio
@patch("src.handlers.conversational.chat_async")
async def test_conversational_handler_retries(mock_chat_async):
    """Test ConversationalHandler retry logic."""
    # Fail first attempt, succeed second
    mock_chat_async.side_effect = [
        Exception("First error"),
        {"content": "Success after retry"}
    ]

    handler = ConversationalHandler(max_retries=2)
    classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)

    result = await handler.handle("test", "user123", classification)

    assert result.is_success()
    assert "Success after retry" in result.content
    assert mock_chat_async.call_count == 2  # Initial + 1 retry


@pytest.mark.asyncio
@patch("src.handlers.conversational.chat_async")
async def test_conversational_handler_max_retries_exceeded(mock_chat_async):
    """Test ConversationalHandler when max retries exceeded."""
    mock_chat_async.side_effect = Exception("Always fails")

    handler = ConversationalHandler(max_retries=2)
    classification = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)

    result = await handler.handle("test", "user123", classification)

    assert result.is_error()
    assert mock_chat_async.call_count == 3  # Initial + 2 retries
