"""Tests for retrieval tools."""

import json
import pytest
from unittest.mock import MagicMock, patch

from tools.retrieval_tools import (
    init_retrieval_tools,
    dense_retrieve,
    bm25_retrieve,
    hybrid_retrieve,
)


@pytest.fixture
def mock_qdrant_store():
    """Mock Qdrant store."""
    store = MagicMock()
    return store


@pytest.fixture
def mock_bm25_index():
    """Mock BM25 index."""
    index = MagicMock()
    index.search = MagicMock(return_value=[
        {
            "content": "Test document 1",
            "metadata": {"document_id": "doc1", "chunk_index": 0},
            "score": 0.95,
        },
        {
            "content": "Test document 2",
            "metadata": {"document_id": "doc2", "chunk_index": 1},
            "score": 0.85,
        },
    ])
    return index


@pytest.fixture
def mock_embedding_fn():
    """Mock embedding function."""
    return MagicMock(return_value=[0.1, 0.2, 0.3])


@pytest.fixture
def initialized_tools(mock_qdrant_store, mock_bm25_index, mock_embedding_fn):
    """Initialize tools with mocks."""
    init_retrieval_tools(
        qdrant_store=mock_qdrant_store,
        bm25_index=mock_bm25_index,
        embedding_fn=mock_embedding_fn,
    )
    yield mock_qdrant_store, mock_bm25_index, mock_embedding_fn
    # Reset after test
    init_retrieval_tools(None, None, None)


class TestDenseRetrieve:
    """Tests for dense_retrieve tool."""

    def test_dense_retrieve_basic(self, initialized_tools):
        """Test basic dense retrieval."""
        mock_store, _, _ = initialized_tools

        with patch('indexing.qdrant_store.search_similar') as mock_search:
            mock_search.return_value = [
                {
                    "id": "1",
                    "text": "Result 1",
                    "document_id": "doc1",
                    "chunk_index": 0,
                    "score": 0.9,
                },
            ]

            result = dense_retrieve.invoke({
                "query": "test query",
                "k": 5,
                "user_id": "user123",
            })

            response = json.loads(result)
            assert isinstance(response, list)
            assert len(response) == 1
            assert response[0]["text"] == "Result 1"

    def test_dense_retrieve_with_defaults(self, initialized_tools):
        """Test dense retrieval with default parameters."""
        with patch('indexing.qdrant_store.search_similar') as mock_search:
            mock_search.return_value = []

            result = dense_retrieve.invoke({"query": "test"})

            response = json.loads(result)
            assert isinstance(response, list)

    def test_dense_retrieve_not_initialized(self):
        """Test error when store not initialized."""
        init_retrieval_tools(None, None, None)

        result = dense_retrieve.invoke({"query": "test"})
        # Should raise RuntimeError
        assert "RuntimeError" in result or "not initialized" in result.lower()


class TestBM25Retrieve:
    """Tests for bm25_retrieve tool."""

    def test_bm25_retrieve_basic(self, initialized_tools):
        """Test basic BM25 retrieval."""
        _, mock_index, _ = initialized_tools

        result = bm25_retrieve.invoke({
            "query": "test query",
            "k": 5,
        })

        response = json.loads(result)
        assert isinstance(response, list)
        assert len(response) == 2
        assert response[0]["content"] == "Test document 1"
        assert mock_index.search.called

    def test_bm25_retrieve_no_index(self):
        """Test BM25 retrieval when no index available."""
        init_retrieval_tools(None, None, None)

        result = bm25_retrieve.invoke({"query": "test", "k": 5})
        # Should raise RuntimeError
        assert "not available" in result.lower() or "runtime" in result.lower()


class TestHybridRetrieve:
    """Tests for hybrid_retrieve tool."""

    def test_hybrid_retrieve_with_bm25(self, initialized_tools):
        """Test hybrid retrieval with both dense and BM25."""
        mock_store, mock_index, _ = initialized_tools

        with patch('indexing.qdrant_store.search_similar') as mock_search:
            mock_search.return_value = [
                {
                    "id": "1",
                    "text": "Dense result 1",
                    "document_id": "doc1",
                    "chunk_index": 0,
                    "score": 0.9,
                },
            ]

            result = hybrid_retrieve.invoke({
                "query": "test query",
                "k": 5,
                "user_id": "user123",
            })

            response = json.loads(result)
            assert isinstance(response, list)
            # Should fuse both results
            assert len(response) > 0

    def test_hybrid_retrieve_dense_only(self, initialized_tools):
        """Test hybrid retrieval falls back to dense only."""
        mock_store, _, _ = initialized_tools

        # Initialize without BM25
        init_retrieval_tools(qdrant_store=mock_store, bm25_index=None)

        with patch('indexing.qdrant_store.search_similar') as mock_search:
            mock_search.return_value = [
                {
                    "id": "1",
                    "text": "Dense result",
                    "document_id": "doc1",
                    "chunk_index": 0,
                    "score": 0.9,
                },
            ]

            result = hybrid_retrieve.invoke({
                "query": "test query",
                "k": 5,
            })

            response = json.loads(result)
            assert isinstance(response, list)

    def test_hybrid_retrieve_custom_rrf_k(self, initialized_tools):
        """Test hybrid retrieval with custom RRF parameter."""
        mock_store, mock_index, _ = initialized_tools

        with patch('indexing.qdrant_store.search_similar') as mock_search:
            mock_search.return_value = []

            result = hybrid_retrieve.invoke({
                "query": "test",
                "k": 5,
                "rrf_k": 100,
            })

            response = json.loads(result)
            assert isinstance(response, list)
