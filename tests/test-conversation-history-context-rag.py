"""Test conversation context in RAG chat flow."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import uuid


class TestConversationContext:
    """Test conversation history is passed through the entire flow."""

    @pytest.mark.asyncio
    async def test_conversation_history_loaded_in_chat_api(self):
        """Test that conversation history is loaded when conversation_id is provided."""
        from src.api.chat import _stream_generator_v2
        from src.indexing.document_store import get_conversation_messages
        from unittest.mock import patch

        # Mock conversation with messages
        mock_messages = [
            MagicMock(role="user", content="Quy định về nghỉ phép?"),
            MagicMock(role="assistant", content="Theo quy định..."),
        ]

        # Mock the database calls
        with patch("src.api.chat.get_conversation_messages", new=AsyncMock(return_value=mock_messages)):
            with patch("src.api.chat.get_orchestrator") as mock_get_orch:
                mock_orch = MagicMock()
                mock_orch.query_stream = AsyncMock(return_value=[
                    {"type": "routing", "data": {"router": "RAGRouter"}},
                    {"type": "content", "data": {"text": "Test response"}},
                    {"type": "metadata", "data": {"status": "success"}},
                ])
                mock_get_orch.return_value = mock_orch

                # Collect chunks
                chunks = []
                async for chunk in _stream_generator_v2(
                    query="Về ngày nghỉ lễ thì sao?",
                    user_id=uuid.uuid4(),
                    conversation_id=uuid.uuid4(),
                    db=AsyncMock(),
                ):
                    chunks.append(chunk)

                # Verify orchestrator was called with conversation history
                mock_orch.query_stream.assert_called_once()
                call_args = mock_orch.query_stream.call_args
                history = call_args[1].get("conversation_history")

                assert history is not None, "Conversation history should be passed"
                assert len(history) == 2, f"Expected 2 messages, got {len(history)}"
                assert history[0]["role"] == "user"
                assert history[0]["content"] == "Quy định về nghỉ phép?"

    @pytest.mark.asyncio
    async def test_conversation_history_passed_to_orchestrator(self):
        """Test that orchestrator receives and passes history to routers."""
        from src.agents.orchestrator import OrchestratorAgent
        from src.agents.routers.registry import RouterRegistry

        # Setup
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]

        with patch("src.agents.routers.registry.RouterRegistry.route") as mock_route:
            mock_route.return_value = {"content": "Test response", "status": "success"}

            orchestrator = OrchestratorAgent(auto_register=False)
            await orchestrator.query(
                user_query="New question",
                user_id="test_user",
                conversation_history=history,
            )

            # Verify history was passed to RouterRegistry
            mock_route.assert_called_once()
            call_args = mock_route.call_args
            assert call_args[1]["conversation_history"] == history

    @pytest.mark.asyncio
    async def test_conversation_history_passed_to_rag_router(self):
        """Test that RAG router receives and passes history to RAG agent."""
        from src.agents.routers.rag import RAGRouter
        from src.agents.rag_agent import AgenticRAG

        history = [
            {"role": "user", "content": "Quy định về nghỉ phép?"},
            {"role": "assistant", "content": "Theo quy định..."},
        ]

        with patch.object(AgenticRAG, "query", new=AsyncMock(return_value={
            "content": "Response",
            "citations": [],
            "status": "success"
        })) as mock_query:
            router = RAGRouter()
            result = await router.handle(
                query="Về ngày nghỉ lễ thì sao?",
                user_id="test_user",
                conversation_history=history,
            )

            # Verify history was passed to RAG agent
            mock_query.assert_called_once()
            call_args = mock_query.call_args
            assert call_args[1]["conversation_history"] == history

    @pytest.mark.asyncio
    async def test_query_rewriting_with_history(self):
        """Test that query is rewritten using conversation history."""
        from src.agents.rag_agent import AgenticRAG

        agent = AgenticRAG(max_iterations=1)

        history = [
            {"role": "user", "content": "Quy định về nghỉ phép?"},
            {"role": "assistant", "content": "Theo Luật Lao động, người lao động có quyền nghỉ phép năm..."},
        ]

        with patch("src.agents.rag_agent.chat_async") as mock_chat:
            mock_chat.return_value = {"content": "Quy định về ngày nghỉ lễ trong phép năm"}

            rewritten = await agent._rewrite_query_with_history("Về ngày nghỉ lễ thì sao?", history)

            # Should be rewritten to be more specific
            assert rewritten != "Về ngày nghỉ lễ thì sao?"
            assert "nghỉ lễ" in rewritten.lower() or "phép" in rewritten.lower()

    @pytest.mark.asyncio
    async def test_no_history_returns_original_query(self):
        """Test that without history, query remains unchanged."""
        from src.agents.rag_agent import AgenticRAG

        agent = AgenticRAG()
        original_query = "Quy định về nghỉ phép?"

        rewritten = await agent._rewrite_query_with_history(original_query, None)

        assert rewritten == original_query

    @pytest.mark.asyncio
    async def test_generate_answer_includes_history(self):
        """Test that LLM prompt includes conversation history."""
        from src.agents.rag_agent import AgenticRAG

        agent = AgenticRAG()

        history = [
            {"role": "user", "content": "Quy định về nghỉ phép?"},
            {"role": "assistant", "content": "Theo quy định..."},
        ]

        with patch("src.agents.rag_agent.chat_async") as mock_chat:
            mock_chat.return_value = {"content": "Answer with context"}

            await agent.generate_answer(
                query="Về ngày nghỉ lễ thì sao?",
                docs=[],
                conversation_history=history,
            )

            # Verify chat_async received history in messages
            mock_chat.assert_called_once()
            call_args = mock_chat.call_args
            messages = call_args[1]["messages"]

            # Should have system prompt + history + user query
            assert len(messages) >= 3  # system + 2 history messages + current query

            # Check that history is included
            history_in_messages = [m for m in messages if m["role"] in ["user", "assistant"]]
            assert len(history_in_messages) >= 2

    @pytest.mark.asyncio
    async def test_conversational_router_uses_history(self):
        """Test that ConversationalRouter includes history in LLM call."""
        from src.agents.routers.conversational import ConversationalRouter

        router = ConversationalRouter()

        history = [
            {"role": "user", "content": "Xin chào"},
            {"role": "assistant", "content": "Chào bạn!"},
        ]

        with patch("src.agents.routers.conversational.chat_async") as mock_chat:
            mock_chat.return_value = {"content": "Chào bạn lần nữa!"}

            await router.handle(
                query="Bạn khỏe không?",
                user_id="test_user",
                conversation_history=history,
            )

            # Verify history was passed
            mock_chat.assert_called_once()
            call_args = mock_chat.call_args
            messages = call_args[1]["messages"]

            # Should have system + history + current query
            assert len(messages) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
