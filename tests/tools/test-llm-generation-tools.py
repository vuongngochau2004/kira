"""Tests for LLM generation tools."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tools.llm_generation_tools import (
    init_llm_tools,
    generate_tool,
    chat_with_history_tool,
    generate_with_tools_tool,
    estimate_tokens_tool,
    validate_prompt_tool,
)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = MagicMock()
    client.chat_async = AsyncMock(return_value={
        "content": "Test response",
        "model": "glm-4.5",
        "provider": "glm",
    })
    return client


@pytest.fixture
def initialized_tools(mock_llm_client):
    """Initialize tools with mock client."""
    init_llm_tools(mock_llm_client)
    yield mock_llm_client
    # Reset after test
    init_llm_tools(None)


class TestGenerateTool:
    """Tests for generate_tool."""

    def test_generate_tool_basic(self, initialized_tools):
        """Test basic text generation."""
        result = generate_tool.invoke({
            "prompt": "What is RAG?",
            "temperature": 0.5,
            "max_tokens": 1000,
        })

        response = json.loads(result)
        assert response["success"] is True
        assert "content" in response
        assert response["model"] == "glm-4.5"
        assert response["provider"] == "glm"

    def test_generate_tool_with_default_params(self, initialized_tools):
        """Test generation with default parameters."""
        result = generate_tool.invoke({"prompt": "Hello"})

        response = json.loads(result)
        assert response["success"] is True
        assert initialized_tools.chat_async.called

    def test_generate_tool_not_initialized(self):
        """Test error when LLM client not initialized."""
        # Reset initialization
        init_llm_tools(None)

        result = generate_tool.invoke({"prompt": "Test"})
        response = json.loads(result)

        assert response["success"] is False
        assert "error" in response


class TestChatWithHistoryTool:
    """Tests for chat_with_history_tool."""

    def test_chat_with_history(self, initialized_tools):
        """Test chat with conversation history."""
        history = json.dumps([
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ])

        result = chat_with_history_tool.invoke({
            "message": "How are you?",
            "history": history,
        })

        response = json.loads(result)
        assert response["success"] is True
        assert "content" in response

    def test_chat_with_history_and_system_prompt(self, initialized_tools):
        """Test chat with system prompt."""
        history = json.dumps([])

        result = chat_with_history_tool.invoke({
            "message": "Help me",
            "history": history,
            "system_prompt": "You are a helpful assistant.",
        })

        response = json.loads(result)
        assert response["success"] is True

    def test_chat_with_empty_history(self, initialized_tools):
        """Test chat with empty history."""
        result = chat_with_history_tool.invoke({
            "message": "Test",
            "history": "[]",
        })

        response = json.loads(result)
        assert response["success"] is True


class TestGenerateWithToolsTool:
    """Tests for generate_with_tools_tool."""

    def test_generate_with_tools(self, initialized_tools):
        """Test generation with tool definitions."""
        with patch('tools.llm_generation_tools.chat_async_with_tools') as mock_chat_with_tools:
            mock_chat_with_tools.return_value = {
                "content": "Tool use response",
                "tool_results": [{"tool_name": "test", "tool_input": {"arg": "value"}}],
                "model": "glm-4.5",
                "provider": "glm",
                "stop_reason": "tool_use",
            }

            tools = json.dumps([{
                "name": "extract_info",
                "description": "Extract information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
            }])

            result = generate_with_tools_tool.invoke({
                "prompt": "Extract name from text",
                "tools": tools,
            })

            response = json.loads(result)
            assert response["success"] is True
            assert "tool_results" in response
            assert len(response["tool_results"]) > 0

    def test_generate_with_tools_empty(self, initialized_tools):
        """Test error when no tools provided."""
        result = generate_with_tools_tool.invoke({
            "prompt": "Test",
            "tools": "[]",
        })

        response = json.loads(result)
        assert response["success"] is False
        assert "No tool definitions" in response["error"]


class TestEstimateTokensTool:
    """Tests for estimate_tokens_tool."""

    def test_estimate_english_text(self):
        """Test token estimation for English text."""
        text = "This is a test sentence with some words."
        result = estimate_tokens_tool.invoke({"text": text})

        response = json.loads(result)
        assert response["success"] is True
        assert response["text_length"] == len(text)
        assert response["has_vietnamese"] is False
        assert response["estimated_tokens"] > 0

    def test_estimate_vietnamese_text(self):
        """Test token estimation for Vietnamese text."""
        result = estimate_tokens_tool.invoke({
            "text": "Xin chào, đây là một câu tiếng Việt.",
        })

        response = json.loads(result)
        assert response["success"] is True
        assert response["has_vietnamese"] is True
        # Vietnamese should have higher token estimate
        assert response["estimated_tokens"] > 0

    def test_estimate_empty_text(self):
        """Test token estimation for empty text."""
        result = estimate_tokens_tool.invoke({"text": ""})

        response = json.loads(result)
        assert response["success"] is True
        assert response["text_length"] == 0
        assert response["estimated_tokens"] >= 0


class TestValidatePromptTool:
    """Tests for validate_prompt_tool."""

    def test_validate_good_prompt(self):
        """Test validation of good prompt."""
        result = validate_prompt_tool.invoke({
            "prompt": "What is the meaning of life? Please explain in detail.",
        })

        response = json.loads(result)
        assert response["success"] is True
        assert response["is_valid"] is True
        assert len(response["issues"]) == 0

    def test_validate_short_prompt(self):
        """Test validation of short prompt."""
        result = validate_prompt_tool.invoke({
            "prompt": "Hi",
            "min_length": 10,
        })

        response = json.loads(result)
        assert response["success"] is True
        assert response["is_valid"] is False
        assert any("too short" in issue for issue in response["issues"])

    def test_validate_long_prompt(self):
        """Test validation of long prompt."""
        long_text = "Test " * 3000  # > 10000 chars
        result = validate_prompt_tool.invoke({
            "prompt": long_text,
            "max_length": 10000,
        })

        response = json.loads(result)
        assert response["success"] is True
        assert response["is_valid"] is False
        assert any("too long" in issue for issue in response["issues"])

    def test_validate_empty_prompt(self):
        """Test validation of empty prompt."""
        result = validate_prompt_tool.invoke({"prompt": "   "})

        response = json.loads(result)
        assert response["success"] is True
        assert response["is_valid"] is False
        assert any("empty" in issue for issue in response["issues"])

    def test_validate_vietnamese_prompt(self):
        """Test validation detects Vietnamese."""
        result = validate_prompt_tool.invoke({
            "prompt": "Xin chào, hãy giúp tôi tìm thông tin.",
        })

        response = json.loads(result)
        assert response["success"] is True
        assert response["has_vietnamese"] is True
        assert any("Vietnamese" in sugg for sugg in response["suggestions"])

    def test_validate_ambiguous_prompt(self):
        """Test validation detects ambiguous language."""
        result = validate_prompt_tool.invoke({
            "prompt": "Tell me about something interesting.",
        })

        response = json.loads(result)
        assert response["success"] is True
        # Should suggest being more specific
        assert len(response["suggestions"]) > 0

    def test_validate_provides_suggestions(self):
        """Test validation provides helpful suggestions."""
        result = validate_prompt_tool.invoke({
            "prompt": "test",  # No punctuation, lowercase
        })

        response = json.loads(result)
        assert response["success"] is True
        assert len(response["suggestions"]) > 0
