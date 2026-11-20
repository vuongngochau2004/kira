"""Provider-neutral LLM adapter for request-scoped call accounting."""

import time
from contextlib import aclosing
from typing import Any, AsyncIterator

from src.shared.ports.llm import LLMPort
from src.shared.utils.request_trace import record_model_call


class TracedLLMPort(LLMPort):
    """Delegate to an LLM port and count completed or failed calls."""

    def __init__(self, inner: LLMPort) -> None:
        self.inner = inner

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        """Generate a response and record the call outcome."""
        started = time.perf_counter()
        outcome = "completed"
        try:
            return await self.inner.generate(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except BaseException:
            outcome = "interrupted"
            raise
        finally:
            record_model_call((time.perf_counter() - started) * 1000, outcome)

    async def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Forward provider tokens and close the upstream stream on cancellation."""
        started = time.perf_counter()
        outcome = "completed"
        try:
            async with aclosing(
                self.inner.stream(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            ) as stream:
                async for chunk in stream:
                    yield chunk
        except BaseException:
            outcome = "interrupted"
            raise
        finally:
            record_model_call((time.perf_counter() - started) * 1000, outcome)

    async def health_check(self) -> bool:
        """Forward the provider health check."""
        return await self.inner.health_check()
