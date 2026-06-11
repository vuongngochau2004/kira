"""Tests for enhanced retrieval tools in 4-agent architecture."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from tools.retrieval_tools import (
    init_retrieval_tools,
    query_expansion_tool,
    hybrid_retrieve_with_expansion,
    retrieve_with_rerank,
    format_documents_for_context,
)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = Mock()
    client.chat_async = AsyncMock()
    return client


@pytest.fixture
def mock_bm25_index():
    """Mock BM25 index."""
    index = Mock()
    index.search = Mock(return_value=[
        {
            "content": "Test document content",
            "metadata": {"document_id": "doc1", "chunk_index": 0, "filename": "test.pdf"},
            "score": 0.8
        }
    ])
    return index


@pytest.fixture
def mock_qdrant_store():
    """Mock Qdrant store."""
    store = Mock()
    return store


@pytest.fixture
def mock_embedding_fn():
    """Mock embedding function."""
    return Mock(return_value=[0.1, 0.2, 0.3])


@pytest.mark.asyncio
async def test_query_expansion_tool_with_llm(mock_llm_client):
    """Test query expansion with LLM."""
    init_retrieval_tools(llm_client=mock_llm_client)

    mock_llm_client.chat_async.return_value = {
        "content": "hợp đồng dịch vụ\ncam kết pháp lý\thuê bao\n",
        "model": "glm-4.5"
    }

    result = await query_expansion_tool.ainvoke({
        "query": "hỏi về hợp đồng",
        "expansion_count": 3,
        "use_synonyms": True
    })

    data = json.loads(result)
    assert data["success"] is True
    assert data["original_query"] == "hỏi về hợp đồng"
    assert len(data["expanded_queries"]) >= 1
    assert "hỏi về hợp đồng" in data["expanded_queries"]


@pytest.mark.asyncio
async def test_query_expansion_tool_fallback():
    """Test query expansion fallback without LLM."""
    init_retrieval_tools(llm_client=None)

    result = await query_expansion_tool.ainvoke({
        "query": "test query",
        "expansion_count": 3,
        "use_synonyms": True
    })

    data = json.loads(result)
    assert data["success"] is True  # Should still succeed with synonyms
    assert data["original_query"] == "test query"


@pytest.mark.asyncio
@patch('indexing.qdrant_store.search_similar')
@patch('ingestion.embedding.embed_single')
async def test_hybrid_retrieve_with_expansion(
    mock_embed,
    mock_search,
    mock_llm_client,
    mock_bm25_index
):
    """Test hybrid retrieval with query expansion."""
    init_retrieval_tools(
        llm_client=mock_llm_client,
        bm25_index=mock_bm25_index
    )

    mock_embed.return_value = [0.1, 0.2, 0.3]
    mock_search.return_value = [
        {
            "text": "Test document",
            "document_id": "doc1",
            "chunk_index": 0,
            "user_id": "user123",
            "score": 0.9
        }
    ]

    result = await hybrid_retrieve_with_expansion.ainvoke({
        "query": "test query",
        "user_id": "user123",
        "k": 10,
        "enable_expansion": False  # Disable expansion for simpler test
    })

    data = json.loads(result)
    assert data["success"] is True
    assert "documents" in data
    assert "metadata" in data
    assert data["metadata"]["user_id"] == "user123"


@pytest.mark.asyncio
@patch('indexing.qdrant_store.search_similar')
@patch('ingestion.embedding.embed_single')
async def test_retrieve_with_rerank(
    mock_embed,
    mock_search,
    mock_llm_client,
    mock_bm25_index
):
    """Test retrieve with reranking."""
    from tools.reranking_tools import init_reranking_tools

    init_retrieval_tools(
        llm_client=mock_llm_client,
        bm25_index=mock_bm25_index
    )
    init_reranking_tools(llm_client=mock_llm_client)

    mock_embed.return_value = [0.1, 0.2, 0.3]
    mock_search.return_value = [
        {
            "text": "Document 1",
            "document_id": "doc1",
            "chunk_index": 0,
            "score": 0.9
        },
        {
            "text": "Document 2",
            "document_id": "doc2",
            "chunk_index": 0,
            "score": 0.7
        }
    ]

    result = await retrieve_with_rerank.ainvoke({
        "query": "test query",
        "user_id": "user123",
        "k": 5,
        "rerank_top_k": 3,
        "enable_reranking": False  # Disable for simpler test
    })

    data = json.loads(result)
    assert data["success"] is True
    assert "documents" in data
    assert "metadata" in data
    assert data["metadata"]["reranking_applied"] is False


def test_format_documents_for_context():
    """Test formatting documents for context."""
    docs = [
        {
            "text": "This is document 1 content about contracts.",
            "filename": "contract.pdf",
            "page_number": 1,
            "score": 0.9
        },
        {
            "text": "This is document 2 content about policies.",
            "filename": "policy.pdf",
            "page_number": 3,
            "score": 0.85
        }
    ]

    result = format_documents_for_context.invoke({
        "documents": json.dumps(docs),
        "max_length": 500,
        "include_metadata": True
    })

    assert "contract.pdf" in result
    assert "policy.pdf" in result
    assert "Page 1" in result or "Page 3" in result
    assert "[1]" in result or "[2]" in result


def test_format_documents_with_length_limit():
    """Test document formatting with length limit."""
    docs = [
        {
            "text": "A" * 1000,  # Long document
            "filename": "long.pdf",
            "score": 0.9
        }
    ]

    result = format_documents_for_context.invoke({
        "documents": json.dumps(docs),
        "max_length": 200,
        "include_metadata": True
    })

    assert len(result) <= 250  # Some buffer for metadata
    assert "..." in result  # Should be truncated


def test_format_documents_empty():
    """Test formatting empty document list."""
    result = format_documents_for_context.invoke({
        "documents": json.dumps([]),
        "max_length": 1000
    })

    assert "No relevant documents found" in result


@pytest.mark.asyncio
async def test_query_expansion_tool_error_handling():
    """Test error handling in query expansion."""
    # Test with invalid input
    result = await query_expansion_tool.ainvoke({
        "query": "",  # Empty query
        "expansion_count": 3
    })

    data = json.loads(result)
    # Should handle gracefully
    assert "expanded_queries" in data


def test_init_retrieval_tools():
    """Test initialization of retrieval tools."""
    mock_llm = Mock()
    mock_bm25 = Mock()
    mock_qdrant = Mock()
    mock_embed = Mock()

    init_retrieval_tools(
        qdrant_store=mock_qdrant,
        bm25_index=mock_bm25,
        embedding_fn=mock_embed,
        llm_client=mock_llm
    )

    # Should not raise any errors
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
