"""
Unit Tests for Basic 2-Node Agentic RAG Graph (4-Agent Architecture)

Tests cover:
- Graph compilation
- State flow between nodes
- Error handling
- Edge cases
- Mock agent behavior

Run with:
    pytest tests/agentic_rag/test_basic_2_node_graph.py -v
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from graphs.basic_2_node_graph import (
    create_basic_graph,
    execute_basic_graph,
    retrieval_node,
    generation_node,
    should_continue_generation,
    should_end,
    create_test_state,
    print_graph_structure
)
from models.agentic_rag_state import (
    RAGState,
    AgentStatus,
    RetrievalAgentConfig,
    GenerationAgentConfig,
    create_initial_state,
    DocumentWithScore
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = Mock()
    client.generate = AsyncMock(return_value="Test response from LLM")
    client.generate_stream = AsyncMock()

    # Setup streaming to yield chunks
    async def stream_generator(*args, **kwargs):
        chunks = ["Test ", "response ", "from ", "LLM"]
        for chunk in chunks:
            yield chunk

    client.generate_stream.side_effect = stream_generator
    return client


@pytest.fixture
def mock_retrieval_agent():
    """Mock RetrievalAgent for testing."""
    agent = Mock()

    async def mock_handle(state):
        # Add mock documents to state
        mock_docs = [
            DocumentWithScore(
                doc_id=uuid4(),
                content="Test document content",
                filename="test.pdf",
                page_number=1,
                chunk_index=0,
                score=0.85,
                metadata={"test": True}
            )
        ]

        from models.agentic_rag_state import update_retrieval_output
        return update_retrieval_output(
            state=state,
            refined_queries=["test query", "test query expanded"],
            retrieved_docs=mock_docs,
            reranked_docs=mock_docs,
            metadata=None
        )

    agent.handle = mock_handle
    return agent


@pytest.fixture
def mock_generation_agent():
    """Mock GenerationAgent for testing."""
    agent = Mock()

    async def mock_handle(state):
        state["generated_response"] = "Test generated response"
        state["generation_metadata"] = {"model": "test", "tokens": 100}
        return state

    agent.handle = mock_handle
    return agent


@pytest.fixture
def sample_state():
    """Create sample RAGState for testing."""
    return create_initial_state(
        query="test query",
        user_id="test_user",
        conversation_id=uuid4()
    )


# ============================================================================
# Graph Creation Tests
# ============================================================================

class TestGraphCreation:
    """Test graph creation and compilation."""

    @pytest.mark.asyncio
    async def test_create_basic_graph(self):
        """Test basic graph creation."""
        graph = create_basic_graph()

        assert graph is not None
        assert hasattr(graph, 'ainvoke')
        assert hasattr(graph, 'astream')

    @pytest.mark.asyncio
    async def test_graph_with_checkpointer(self):
        """Test graph creation with checkpointer."""
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        graph = create_basic_graph(checkpointer=checkpointer)

        assert graph is not None

    def test_print_graph_structure(self, capsys):
        """Test graph structure printing."""
        print_graph_structure()

        captured = capsys.readouterr()
        assert "Basic 2-Node Agentic RAG Graph Structure" in captured.out
        assert "retrieval" in captured.out
        assert "generation" in captured.out


# ============================================================================
# Node Function Tests
# ============================================================================

class TestRetrievalNode:
    """Test retrieval node functionality."""

    @pytest.mark.asyncio
    async def test_retrieval_node_success(self, sample_state, mock_retrieval_agent):
        """Test successful retrieval execution."""
        # Patch RetrievalAgent instantiation
        with patch('graphs.basic_2_node_graph.RetrievalAgent',
                   return_value=mock_retrieval_agent):
            result = await retrieval_node(sample_state)

            assert "retrieval_agent_output" in result
            assert "agent_results" in result
            assert len(sample_state.get("errors", [])) == 0

    @pytest.mark.asyncio
    async def test_retrieval_node_failure(self, sample_state):
        """Test retrieval node error handling."""
        # Patch RetrievalAgent to raise exception
        with patch('graphs.basic_2_node_graph.RetrievalAgent',
                   side_effect=Exception("Retrieval failed")):
            result = await retrieval_node(sample_state)

            assert "errors" in result
            assert result["should_fallback"] == True
            assert result["fallback_reason"] is not None

    @pytest.mark.asyncio
    async def test_retrieval_node_timing(self, sample_state, mock_retrieval_agent):
        """Test retrieval node tracks execution time."""
        import time

        with patch('graphs.basic_2_node_graph.RetrievalAgent',
                   return_value=mock_retrieval_agent):
            start_time = time.time()
            result = await retrieval_node(sample_state)
            execution_time = (time.time() - start_time) * 1000

            # Should complete in reasonable time
            assert execution_time < 5000  # 5 seconds max


class TestGenerationNode:
    """Test generation node functionality."""

    @pytest.mark.asyncio
    async def test_generation_node_success(self, sample_state, mock_llm_client, mock_generation_agent):
        """Test successful generation execution."""
        # Setup state with retrieval output
        from models.agentic_rag_state import update_retrieval_output, DocumentWithScore

        mock_docs = [
            DocumentWithScore(
                doc_id=uuid4(),
                content="Test content",
                filename="test.pdf",
                page_number=1,
                chunk_index=0,
                score=0.85
            )
        ]

        sample_state = update_retrieval_output(
            state=sample_state,
            refined_queries=["test"],
            retrieved_docs=mock_docs,
            reranked_docs=mock_docs
        )

        # Add LLM client to state
        sample_state["llm_client"] = mock_llm_client

        # Patch GenerationAgent
        with patch('graphs.basic_2_node_graph.GenerationAgent',
                   return_value=mock_generation_agent):
            result = await generation_node(sample_state)

            assert "generated_response" in result
            assert result["generated_response"] != ""

    @pytest.mark.asyncio
    async def test_generation_node_no_documents(self, sample_state):
        """Test generation node when no documents retrieved."""
        result = await generation_node(sample_state)

        assert "generated_response" in result
        assert "không tìm thấy" in result["generated_response"].lower()

    @pytest.mark.asyncio
    async def test_generation_node_retrieval_failed(self, sample_state):
        """Test generation node when retrieval failed."""
        sample_state["should_fallback"] = True

        result = await generation_node(sample_state)

        assert result["current_agent"] == "generation_skipped"

    @pytest.mark.asyncio
    async def test_generation_node_no_llm_client(self, sample_state, mock_generation_agent):
        """Test generation node without LLM client."""
        # Setup state with retrieval output
        from models.agentic_rag_state import update_retrieval_output, DocumentWithScore

        mock_docs = [
            DocumentWithScore(
                doc_id=uuid4(),
                content="Test content",
                filename="test.pdf",
                page_number=1,
                chunk_index=0,
                score=0.85
            )
        ]

        sample_state = update_retrieval_output(
            state=sample_state,
            refined_queries=["test"],
            retrieved_docs=mock_docs,
            reranked_docs=mock_docs
        )

        # Don't add LLM client
        result = await generation_node(sample_state)

        assert "errors" in result
        assert len(result["errors"]) > 0


# ============================================================================
# Conditional Edge Tests
# ============================================================================

class TestConditionalEdges:
    """Test conditional edge logic."""

    def test_should_continue_generation_with_docs(self, sample_state):
        """Test continue to generation when documents exist."""
        from models.agentic_rag_state import update_retrieval_output, DocumentWithScore

        mock_docs = [
            DocumentWithScore(
                doc_id=uuid4(),
                content="Test content",
                filename="test.pdf",
                page_number=1,
                chunk_index=0,
                score=0.85
            ).model_dump()
        ]

        sample_state["retrieval_agent_output"]["reranked_docs"] = mock_docs

        result = should_continue_generation(sample_state)
        assert result == "generation"

    def test_should_continue_generation_no_docs(self, sample_state):
        """Test END when no documents."""
        result = should_continue_generation(sample_state)
        assert result == "end"  # END sentinel

    def test_should_continue_generation_fallback(self, sample_state):
        """Test END when fallback triggered."""
        sample_state["should_fallback"] = True

        result = should_continue_generation(sample_state)
        assert result == "end"  # END sentinel

    def test_should_end(self, sample_state):
        """Test should_end always returns END."""
        result = should_end(sample_state)
        assert result == "end"  # END sentinel


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestHelperFunctions:
    """Test helper functions."""

    def test_create_test_state_basic(self):
        """Test basic test state creation."""
        state = create_test_state()

        assert state["query"] == "test query"
        assert state["user_id"] == "test_user"
        assert "retrieval_agent_output" in state

    def test_create_test_state_with_params(self):
        """Test test state creation with custom parameters."""
        state = create_test_state(
            query="custom query",
            user_id="custom_user",
            include_documents=True
        )

        assert state["query"] == "custom query"
        assert state["user_id"] == "custom_user"
        assert len(state["retrieval_agent_output"]["reranked_docs"]) > 0

    def test_create_test_state_no_documents(self):
        """Test test state creation without documents."""
        state = create_test_state(include_documents=False)

        assert len(state["retrieval_agent_output"]["reranked_docs"]) == 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestGraphIntegration:
    """Integration tests for complete graph execution."""

    @pytest.mark.asyncio
    async def test_execute_basic_graph_success(self, mock_llm_client):
        """Test complete graph execution with successful flow."""
        # Patch agents
        with patch('graphs.basic_2_node_graph.RetrievalAgent') as mock_retrieval_cls, \
             patch('graphs.basic_2_node_graph.GenerationAgent') as mock_gen_cls:

            # Setup mock retrieval agent
            mock_retrieval = Mock()
            async def mock_retrieve_handle(state):
                mock_docs = [
                    DocumentWithScore(
                        doc_id=uuid4(),
                        content="Test content",
                        filename="test.pdf",
                        page_number=1,
                        chunk_index=0,
                        score=0.85
                    )
                ]
                from models.agentic_rag_state import update_retrieval_output
                return update_retrieval_output(state, ["test"], mock_docs, mock_docs, None)

            mock_retrieval.handle = mock_retrieve_handle
            mock_retrieval_cls.return_value = mock_retrieval

            # Setup mock generation agent
            mock_gen = Mock()
            async def mock_gen_handle(state):
                state["generated_response"] = "Test response"
                state["generation_metadata"] = {"model": "test"}
                return state

            mock_gen.handle = mock_gen_handle
            mock_gen_cls.return_value = mock_gen

            # Execute graph
            result = await execute_basic_graph(
                query="test query",
                user_id="test_user",
                llm_client=mock_llm_client
            )

            assert result is not None
            assert result["query"] == "test query"
            assert result["user_id"] == "test_user"
            assert "generated_response" in result

    @pytest.mark.asyncio
    async def test_execute_basic_graph_with_configs(self, mock_llm_client):
        """Test graph execution with custom configs."""
        retrieval_config = RetrievalAgentConfig(
            top_k=5,
            enable_reranking=True
        )
        generation_config = GenerationAgentConfig(
            temperature=0.5,
            max_tokens=1500
        )

        with patch('graphs.basic_2_node_graph.RetrievalAgent') as mock_retrieval_cls, \
             patch('graphs.basic_2_node_graph.GenerationAgent') as mock_gen_cls:

            # Setup mocks
            mock_retrieval = Mock()
            async def mock_retrieve_handle(state):
                from models.agentic_rag_state import update_retrieval_output
                return update_retrieval_output(state, ["test"], [], [], None)

            mock_retrieval.handle = mock_retrieve_handle
            mock_retrieval_cls.return_value = mock_retrieval

            mock_gen = Mock()
            mock_gen.handle = AsyncMock(return_value=None)
            mock_gen_cls.return_value = mock_gen

            result = await execute_basic_graph(
                query="test query",
                user_id="test_user",
                llm_client=mock_llm_client,
                retrieval_config=retrieval_config,
                generation_config=generation_config
            )

            assert result is not None
            assert "config" in result

    @pytest.mark.asyncio
    async def test_execute_basic_graph_error_handling(self, mock_llm_client):
        """Test graph error handling."""
        with patch('graphs.basic_2_node_graph.RetrievalAgent',
                   side_effect=Exception("Graph error")):
            result = await execute_basic_graph(
                query="test query",
                user_id="test_user",
                llm_client=mock_llm_client
            )

            assert result["should_fallback"] == True
            assert result["fallback_reason"] is not None
            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_execute_basic_graph_with_conversation_id(self, mock_llm_client):
        """Test graph execution with conversation context."""
        conversation_id = uuid4()

        with patch('graphs.basic_2_node_graph.RetrievalAgent') as mock_retrieval_cls, \
             patch('graphs.basic_2_node_graph.GenerationAgent') as mock_gen_cls:

            # Setup mocks
            mock_retrieval = Mock()
            async def mock_retrieve_handle(state):
                from models.agentic_rag_state import update_retrieval_output
                return update_retrieval_output(state, ["test"], [], [], None)

            mock_retrieval.handle = mock_retrieve_handle
            mock_retrieval_cls.return_value = mock_retrieval

            mock_gen = Mock()
            mock_gen.handle = AsyncMock(return_value=None)
            mock_gen_cls.return_value = mock_gen

            result = await execute_basic_graph(
                query="test query",
                user_id="test_user",
                conversation_id=conversation_id,
                llm_client=mock_llm_client
            )

            assert result["conversation_id"] == conversation_id


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_query(self, mock_llm_client):
        """Test graph with empty query."""
        with pytest.raises(Exception):
            await execute_basic_graph(
                query="",
                user_id="test_user",
                llm_client=mock_llm_client
            )

    @pytest.mark.asyncio
    async def test_very_long_query(self, mock_llm_client):
        """Test graph with very long query."""
        long_query = "test " * 1000

        with patch('graphs.basic_2_node_graph.RetrievalAgent') as mock_retrieval_cls, \
             patch('graphs.basic_2_node_graph.GenerationAgent') as mock_gen_cls:

            # Setup mocks
            mock_retrieval = Mock()
            mock_retrieval.handle = AsyncMock(return_value=None)
            mock_retrieval_cls.return_value = mock_retrieval

            mock_gen = Mock()
            mock_gen.handle = AsyncMock(return_value=None)
            mock_gen_cls.return_value = mock_gen

            result = await execute_basic_graph(
                query=long_query,
                user_id="test_user",
                llm_client=mock_llm_client
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self, mock_llm_client):
        """Test graph with special characters."""
        special_query = "Hỏi về hợp đồng @#$%^&*() với điều khoản []{}|\\"

        with patch('graphs.basic_2_node_graph.RetrievalAgent') as mock_retrieval_cls, \
             patch('graphs.basic_2_node_graph.GenerationAgent') as mock_gen_cls:

            # Setup mocks
            mock_retrieval = Mock()
            async def mock_retrieve_handle(state):
                from models.agentic_rag_state import update_retrieval_output
                return update_retrieval_output(state, [special_query], [], [], None)

            mock_retrieval.handle = mock_retrieve_handle
            mock_retrieval_cls.return_value = mock_retrieval

            mock_gen = Mock()
            mock_gen.handle = AsyncMock(return_value=None)
            mock_gen_cls.return_value = mock_gen

            result = await execute_basic_graph(
                query=special_query,
                user_id="test_user",
                llm_client=mock_llm_client
            )

            assert result is not None


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_execution_time(self, mock_llm_client):
        """Test graph execution completes within reasonable time."""
        import time

        with patch('graphs.basic_2_node_graph.RetrievalAgent') as mock_retrieval_cls, \
             patch('graphs.basic_2_node_graph.GenerationAgent') as mock_gen_cls:

            # Setup mocks
            mock_retrieval = Mock()
            mock_retrieval.handle = AsyncMock(return_value=None)
            mock_retrieval_cls.return_value = mock_retrieval

            mock_gen = Mock()
            mock_gen.handle = AsyncMock(return_value=None)
            mock_gen_cls.return_value = mock_gen

            start_time = time.time()
            result = await execute_basic_graph(
                query="test query",
                user_id="test_user",
                llm_client=mock_llm_client
            )
            execution_time = (time.time() - start_time) * 1000

            assert execution_time < 10000  # Should complete in < 10 seconds
            assert result["total_execution_time_ms"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
