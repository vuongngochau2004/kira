"""LangChain tool wrappers for LLM operations.

Provides LangChain-compatible tool wrappers for LLM text generation
and streaming operations using the K.I.R.A LLM client.
"""

import asyncio
import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Global LLM client reference
_llm_client: Any = None


def init_llm_tools(llm_client: Any = None) -> None:
    """Initialize global LLM client for tools.

    Args:
        llm_client: LLM client instance with chat_async method
    """
    global _llm_client
    _llm_client = llm_client


def _get_llm_client() -> Any:
    """Get the global LLM client instance.

    Returns:
        LLM client or None if not initialized

    Raises:
        RuntimeError: If LLM client has not been initialized
    """
    if _llm_client is None:
        raise RuntimeError("LLM client not initialized. Call init_llm_tools() first.")
    return _llm_client


@tool
def generate_tool(
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """Generate text using LLM (non-streaming).

    Use this tool when you need to generate text, answer questions,
    or create content without streaming responses.

    Args:
        prompt: Input prompt for generation
        temperature: Sampling temperature (0.0 - 1.0, default: 0.7)
        max_tokens: Maximum tokens to generate (default: 2000)

    Returns:
        JSON string with generated text and metadata

    Example:
        >>> result = generate_tool.invoke({"prompt": "What is RAG?", "temperature": 0.5})
        >>> response = json.loads(result)
        >>> content = response["content"]
    """
    try:
        llm_client = _get_llm_client()

        messages = [
            {"role": "user", "content": prompt}
        ]

        # Run async LLM call in sync context
        response = asyncio.run(llm_client.chat_async(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ))

        return json.dumps({
            "success": True,
            "content": response.get("content", ""),
            "model": response.get("model", ""),
            "provider": response.get("provider", ""),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in generate_tool: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


@tool
def chat_with_history_tool(
    message: str,
    history: str = "[]",
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """Chat with LLM using conversation history.

    Use this tool for multi-turn conversations where context
    from previous messages is important.

    Args:
        message: Current user message
        history: JSON string of conversation history
                Each message should have 'role' and 'content'
        system_prompt: Optional system prompt to guide behavior
        temperature: Sampling temperature (0.0 - 1.0, default: 0.7)
        max_tokens: Maximum tokens to generate (default: 2000)

    Returns:
        JSON string with generated response and metadata

    Example:
        >>> history = json.dumps([
        ...     {"role": "user", "content": "Hello"},
        ...     {"role": "assistant", "content": "Hi there!"}
        ... ])
        >>> result = chat_with_history_tool.invoke({
        ...     "message": "How are you?",
        ...     "history": history
        ... })
    """
    try:
        llm_client = _get_llm_client()

        # Parse history
        messages = json.loads(history) if history else []

        # Add system message if provided
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        # Add current message
        messages.append({"role": "user", "content": message})

        # Run async LLM call
        response = asyncio.run(llm_client.chat_async(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ))

        return json.dumps({
            "success": True,
            "content": response.get("content", ""),
            "model": response.get("model", ""),
            "provider": response.get("provider", ""),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in chat_with_history_tool: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


@tool
def generate_with_tools_tool(
    prompt: str,
    tools: str,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """Generate text with structured output using tool definitions.

    Use this tool when you need the LLM to return structured data
    by defining tool schemas (function calling).

    Args:
        prompt: Input prompt for generation
        tools: JSON string of tool definitions (Anthropic/GLM format)
        system_prompt: Optional system prompt
        temperature: Sampling temperature (0.0 - 1.0, default: 0.7)
        max_tokens: Maximum tokens to generate (default: 2000)

    Returns:
        JSON string with content and tool use results

    Example:
        >>> tools = json.dumps([{
        ...     "name": "extract_info",
        ...     "description": "Extract information",
        ...     "input_schema": {
        ...         "type": "object",
        ...         "properties": {
        ...             "name": {"type": "string"},
        ...             "value": {"type": "number"}
        ...         }
        ...     }
        ... }])
        >>> result = generate_with_tools_tool.invoke({
        ...     "prompt": "Extract name and value",
        ...     "tools": tools
        ... })
    """
    try:
        from agents.llm import chat_async_with_tools

        # Parse tools
        tool_definitions = json.loads(tools) if tools else []

        if not tool_definitions:
            return json.dumps({
                "success": False,
                "error": "No tool definitions provided",
            }, ensure_ascii=False)

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Run async LLM call with tools
        response = asyncio.run(chat_async_with_tools(
            messages=messages,
            tools=tool_definitions,
            temperature=temperature,
            max_tokens=max_tokens,
        ))

        return json.dumps({
            "success": True,
            "content": response.get("content", ""),
            "tool_results": response.get("tool_results", []),
            "model": response.get("model", ""),
            "provider": response.get("provider", ""),
            "stop_reason": response.get("stop_reason"),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in generate_with_tools_tool: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


@tool
def estimate_tokens_tool(
    text: str,
) -> str:
    """Estimate token count for text (rough approximation).

    Use this tool to estimate the number of tokens in text for
    cost estimation and context window planning.

    Args:
        text: Text to estimate tokens for

    Returns:
        JSON string with estimated token count

    Note:
        This is a rough estimate (~1 token ≈ 4 characters for English,
        ~1 token ≈ 3 characters for Vietnamese). Actual token count
        may vary by model.
    """
    try:
        # Rough estimation: Vietnamese uses ~3 chars/token, English ~4 chars/token
        # We'll use a conservative estimate
        char_count = len(text)

        # Detect if text contains Vietnamese characters
        has_vietnamese = any(0xC0 <= ord(c) <= 0x1EF9 for c in text)

        if has_vietnamese:
            estimated_tokens = max(1, char_count // 3)
        else:
            estimated_tokens = max(1, char_count // 4)

        return json.dumps({
            "success": True,
            "text_length": char_count,
            "estimated_tokens": estimated_tokens,
            "has_vietnamese": has_vietnamese,
            "note": "Rough estimate only. Actual token count depends on model.",
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in estimate_tokens_tool: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


@tool
def validate_prompt_tool(
    prompt: str,
    min_length: int = 10,
    max_length: int = 10000,
) -> str:
    """Validate prompt before sending to LLM.

    Use this tool to check if a prompt meets requirements
    and provide suggestions for improvement.

    Args:
        prompt: Prompt to validate
        min_length: Minimum character length (default: 10)
        max_length: Maximum character length (default: 10000)

    Returns:
        JSON string with validation result and suggestions
    """
    try:
        issues = []
        suggestions = []

        # Check length
        char_count = len(prompt)
        if char_count < min_length:
            issues.append(f"Prompt too short ({char_count} < {min_length} chars)")
            suggestions.append("Add more context and details to your prompt")
        elif char_count > max_length:
            issues.append(f"Prompt too long ({char_count} > {max_length} chars)")
            suggestions.append("Consider splitting into multiple prompts")

        # Check for common issues
        if not prompt.strip():
            issues.append("Prompt is empty or whitespace only")
            suggestions.append("Provide meaningful content")

        if not any(terminator in prompt for terminator in [".", "?", "!", "。", "？", "！"]):
            suggestions.append("Consider ending with a question or clear instruction")

        # Check for Vietnamese content
        has_vietnamese = any(0xC0 <= ord(c) <= 0x1EF9 for c in prompt)
        if has_vietnamese:
            suggestions.append("Vietnamese detected - ensure LLM supports Vietnamese well")

        # Check for ambiguous language
        ambiguous_words = ["thing", "stuff", "something", "anything"]
        if any(word in prompt.lower() for word in ambiguous_words):
            suggestions.append("Avoid ambiguous terms - be more specific")

        is_valid = len(issues) == 0

        # Estimate tokens locally
        if has_vietnamese:
            estimated_tokens = max(1, char_count // 3)
        else:
            estimated_tokens = max(1, char_count // 4)

        return json.dumps({
            "success": True,
            "is_valid": is_valid,
            "issues": issues,
            "suggestions": suggestions,
            "char_count": char_count,
            "estimated_tokens": estimated_tokens,
            "has_vietnamese": has_vietnamese,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in validate_prompt_tool: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


__all__ = [
    "init_llm_tools",
    "generate_tool",
    "chat_with_history_tool",
    "generate_with_tools_tool",
    "estimate_tokens_tool",
    "validate_prompt_tool",
]
