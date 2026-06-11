"""GLM Adapter — implements LLMPort using the existing LLMClient.

This adapter wraps src.shared.infrastructure.llm.client.LLMClient
to conform to the LLMPort interface defined in shared/ports/llm.py.

To swap to Claude or GPT-4, create a ClaudeAdapter or OpenAIAdapter
implementing the same LLMPort — no application code changes needed.
"""
from typing import AsyncIterator, Any

from src.shared.ports.llm import LLMPort
from src.shared.infrastructure.llm.client import LLMClient


class GLMAdapter(LLMPort):
    """Adapter: wraps LLMClient to conform to LLMPort.

    Example:
        >>> adapter = GLMAdapter()
        >>> response = await adapter.generate([{"role": "user", "content": "hello"}])
        >>> async for token in adapter.stream([{"role": "user", "content": "hello"}]):
        ...     print(token, end="")
    """

    def __init__(
        self,
        client: LLMClient | None = None,
        **kwargs: Any,
    ):
        """Initialize with an existing LLMClient or create a new one.

        Args:
            client: Optional pre-configured LLMClient instance
            **kwargs: Passed to LLMClient constructor if client is None
        """
        self._client = client or LLMClient(**kwargs)

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        """Generate a complete response from the LLM.

        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            Generated text content
        """
        result = await self._client.chat_async(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return result.get("content", "")

    async def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream response token by token.

        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Yields:
            Text chunks as generated
        """
        async for chunk in self._client.chat_async_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            # Normalize: chunk can be str or dict
            if isinstance(chunk, str):
                yield chunk
            elif isinstance(chunk, dict) and chunk.get("content"):
                yield chunk["content"]

    async def health_check(self) -> bool:
        """Check LLM provider health by sending a minimal request."""
        try:
            result = await self._client.chat_async(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                temperature=0.1,
            )
            return bool(result.get("content"))
        except Exception:
            return False
