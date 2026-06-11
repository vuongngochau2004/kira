"""
Tests for RAGHandler using LangGraph pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.modules.chat.infrastructure.handlers.rag_handler import RAGHandler
from src.shared.kernel.interfaces.classification import ClassificationResult, Intent
from src.modules.rag.domain.state.rag_state import Citation


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
    # Mock LangGraph pipeline
    mock_pipeline = AsyncMock()
    mock_pipeline.run = AsyncMock(return_value={
        "final_response": "Test response",
        "final_citations": [
            {"filename": "test.pdf", "page_number": 1, "text": "Test citation", "score": 0.85}
        ],
        "generation_metadata": {"model": "glm-4.5"},
        "agent_results": [{"agent_name": "RetrievalAgent", "status": "success"}],
        "total_execution_time_ms": 150.0
    })

    handler = RAGHandler()
    handler.pipeline = mock_pipeline
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    result = await handler.handle("test query", "user123", classification)

    assert result.is_success()
    assert result.content == "Test response"
    assert len(result.citations) == 1
    assert result.citations[0].filename == "test.pdf"
    assert result.citations[0].page == 1
    assert result.citations[0].confidence == 0.85
    assert result.metadata["langgraph"] is True
    assert result.metadata["total_execution_time_ms"] == 150.0
    assert result.metadata["agent_results"][0]["agent_name"] == "RetrievalAgent"


@pytest.mark.asyncio
async def test_rag_handler_handle_with_context():
    """Test RAGHandler with conversation context."""
    mock_pipeline = AsyncMock()
    mock_pipeline.run = AsyncMock(return_value={
        "final_response": "Response with context",
        "final_citations": [],
        "generation_metadata": {},
        "agent_results": [],
        "total_execution_time_ms": 100.0
    })

    handler = RAGHandler()
    handler.pipeline = mock_pipeline
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    context = {"conversation_id": uuid4()}
    result = await handler.handle("new query", "user123", classification, context)

    assert result.is_success()
    assert result.content == "Response with context"


@pytest.mark.asyncio
async def test_rag_handler_handle_error():
    """Test RAGHandler error handling."""
    mock_pipeline = AsyncMock()
    mock_pipeline.run = AsyncMock(side_effect=Exception("LangGraph pipeline failed"))

    handler = RAGHandler()
    handler.pipeline = mock_pipeline
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    result = await handler.handle("test query", "user123", classification)

    assert result.is_error()
    assert "LangGraph pipeline failed" in result.error
    assert result.metadata["langgraph"] is True


@pytest.mark.asyncio
async def test_rag_handler_stream():
    """Test RAGHandler streaming."""
    # Mock streaming response
    async def mock_stream(query, user_id, conversation_id=None):
        yield {
            "mode": "updates",
            "chunk": {"orchestrator": {"routing_decision": "retrieval"}},
        }
        yield {
            "mode": "updates",
            "chunk": {
                "retrieval": {
                    "retrieval_agent_output": {
                        "reranked_docs": [{"content": "doc"}],
                        "refined_queries": ["test query"],
                    }
                }
            },
        }
        yield {
            "mode": "updates",
            "chunk": {
                "generation": {
                    "generated_response": "Mock response",
                    "final_citations": [],
                }
            },
        }
        yield {
            "mode": "updates",
            "chunk": {
                "quality": {
                    "final_response": "Mock response",
                    "final_citations": [],
                    "quality_agent_output": {"quality_score": 0.9},
                }
            },
        }

    mock_pipeline = AsyncMock()
    mock_pipeline.run_stream = mock_stream

    handler = RAGHandler()
    handler.pipeline = mock_pipeline
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    chunks = []
    async for chunk in handler.handle_stream("test query", "user123", classification):
        chunks.append(chunk)

    # chunks:
    # 0: routing chunk
    # 1-4: LangGraph node status updates
    # 5: generation content snapshot
    # 6: metadata chunk
    # 7: done chunk
    assert len(chunks) == 8
    assert chunks[0]["type"] == "routing"
    assert chunks[0]["data"]["router"] == "LangGraphRAGPipeline"
    assert chunks[1]["type"] == "status"
    assert chunks[1]["data"]["stage"] == "orchestrator"
    assert chunks[3]["type"] == "status"
    assert chunks[3]["data"]["stage"] == "generation"
    assert chunks[4]["type"] == "content"
    assert chunks[4]["data"]["text"] == "Mock response"
    assert chunks[6]["type"] == "metadata"
    assert chunks[7]["type"] == "done"


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
    mock_pipeline = AsyncMock()

    async def mock_stream(query, user_id, conversation_id=None):
        yield {
            "mode": "updates",
            "chunk": {"orchestrator": {"routing_decision": "retrieval"}},
        }
        raise Exception("Stream error")

    mock_pipeline.run_stream = mock_stream

    handler = RAGHandler()
    handler.pipeline = mock_pipeline
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    chunks = []
    async for chunk in handler.handle_stream("query", "user123", classification):
        chunks.append(chunk)

    # Should get routing chunk, then node execution, then error, then done
    assert len(chunks) == 4
    assert chunks[0]["type"] == "routing"
    assert chunks[1]["type"] == "status"
    assert chunks[1]["data"]["stage"] == "orchestrator"
    assert chunks[2]["type"] == "error"
    assert chunks[2]["data"]["error"] == "Stream error"
    assert chunks[3]["type"] == "done"


@pytest.mark.asyncio
async def test_rag_handler_custom_config():
    """Test RAGHandler with custom config."""
    from src.shared.kernel.interfaces.handlers import HandlerConfig

    config = HandlerConfig(max_retrieved_docs=10, max_tokens=4000)
    handler = RAGHandler(config=config)

    assert handler.config.max_retrieved_docs == 10
    assert handler.config.max_tokens == 4000


@pytest.mark.asyncio
async def test_rag_handler_citation_conversion():
    """Test citation format conversion."""
    # Test converting both dict-based citations and Citation object-based citations
    citation_obj = Citation(filename="doc2.pdf", page_number=2, text="Citation 2", score=0.8)

    mock_pipeline = AsyncMock()
    mock_pipeline.run = AsyncMock(return_value={
        "final_response": "Response",
        "final_citations": [
            {"filename": "doc1.pdf", "page_number": 1, "text": "Citation 1", "score": 0.9},
            citation_obj
        ],
        "generation_metadata": {},
        "agent_results": [],
        "total_execution_time_ms": 50.0
    })

    handler = RAGHandler()
    handler.pipeline = mock_pipeline
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    result = await handler.handle("query", "user123", classification)

    assert len(result.citations) == 2
    assert result.citations[0].filename == "doc1.pdf"
    assert result.citations[0].confidence == 0.9
    assert result.citations[1].filename == "doc2.pdf"
    assert result.citations[1].confidence == 0.8
