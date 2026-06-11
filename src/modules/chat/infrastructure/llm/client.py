"""
LLM client adapter - Thin wrapper around shared agents.llm module.

This adapter provides a module-local interface to LLM functionality
while delegating to the shared agents.llm module. This follows the
Adapter pattern, allowing the chat module to depend on a local
interface rather than directly on the shared infrastructure.

When agents.llm is eventually migrated to shared/kernel or a
dedicated LLM module, only this adapter needs to change.
"""

from typing import AsyncIterator

from src.shared.infrastructure.llm.client import (
    chat_async,
    chat_async_stream,
    chat_async_with_tools,
    LLMClient,
    LLMProvider,
    LLMError,
    LLMTimeoutError,
    LLMStreamError,
)


class LLMClientAdapter:
    """Adapter wrapping the shared LLM client for chat module use.

    Provides a simplified interface focused on chat module needs:
    - Async chat completion
    - Streaming chat completion
    - Structured output via tool use

    All calls are delegated to agents.llm module functions.
    Configuration (provider, model, temperature) is passed through.
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float | None = None,
    ):
        """Initialize LLM client adapter.

        Args:
            provider: LLM provider (defaults to settings.llm_provider)
            model: Model name (defaults to provider-specific default)
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Max tokens to generate
            timeout: Request timeout in seconds
        """
        self._client = LLMClient(
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, str]:
        """Send a chat request asynchronously (non-streaming).

        Args:
            messages: List of message dicts with role and content
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            Response dict with content, model, provider
        """
        return await self._client.chat_async(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat response chunk by chunk.

        Args:
            messages: List of message dicts with role and content
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Yields:
            Text chunks as they arrive from LLM
        """
        async for chunk in self._client.chat_async_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk

    async def chat_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Send chat request with tool use (structured output).

        Only supported for GLM (Anthropic-compatible) provider.

        Args:
            messages: List of message dicts with role and content
            tools: Tool definitions for function calling
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            Response dict with content, tool_results, model, provider
        """
        return await chat_async_with_tools(
            messages=messages,
            tools=tools,
            temperature=temperature or self._client.temperature,
            max_tokens=max_tokens or self._client.max_tokens,
        )


# Re-export LLM types for convenience
__all__ = [
    "LLMClientAdapter",
    "LLMClient",
    "LLMProvider",
    "LLMError",
    "LLMTimeoutError",
    "LLMStreamError",
]