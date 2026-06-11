"""
Conversational handler for casual chat and greetings.

Handles conversational queries with pre-classified intent.
No retrieval, just direct LLM chat.
"""

import time
import logging
from typing import Any, AsyncIterator
from uuid import UUID

from src.shared.kernel.interfaces.classification import ClassificationResult, Intent
from src.shared.kernel.interfaces.handlers import QueryHandlerBase, HandlerResult, HandlerConfig
from agents.llm import chat_async, chat_async_stream
from agents.llm_post_process import stream_with_thinking_separation
from agents.prompts import (
    CONVERSATIONAL_SYSTEM_PROMPT,
    CONVERSATIONAL_USER_PROMPT,
)


logger = logging.getLogger(__name__)


class ConversationalHandler(QueryHandlerBase):
    """
    Handler for conversational queries (greetings, casual chat).

    Receives pre-classified CONVERSATIONAL queries and executes direct LLM chat.
    No retrieval, no classification logic (SRP compliance).

    Example:
        >>> handler = ConversationalHandler()
        >>> result = await handler.handle("xin chào", "user123", classification)
        >>> assert result.content
    """

    def __init__(
        self,
        config: HandlerConfig | None = None,
        max_retries: int = 2
    ):
        """
        Initialize conversational handler.

        Args:
            config: Optional handler configuration
            max_retries: Max retry attempts for LLM calls
        """
        self.config = config or HandlerConfig()
        self.max_retries = max_retries

    def can_handle(self, classification: ClassificationResult) -> bool:
        """
        Check if handler can handle the classification.

        Args:
            classification: Pre-classified intent and metadata

        Returns:
            True if intent is CONVERSATIONAL
        """
        return classification.intent == Intent.CONVERSATIONAL

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None
    ) -> HandlerResult:
        """
        Execute conversational query (non-streaming).

        Args:
            query: User query string
            user_id: User ID (not used for conversational, but required by protocol)
            classification: Pre-classified intent (must be CONVERSATIONAL)
            context: Additional context (conversation history, etc.)

        Returns:
            HandlerResult with content and metadata

        Raises:
            ValueError: If classification intent is not CONVERSATIONAL
        """
        if classification.intent != Intent.CONVERSATIONAL:
            raise ValueError(f"ConversationalHandler cannot handle intent: {classification.intent}")

        t0 = time.perf_counter()
        conversation_history = context.get("conversation_history") if context else None

        system_content = CONVERSATIONAL_SYSTEM_PROMPT
        user_content = CONVERSATIONAL_USER_PROMPT.format(query=query)

        # Build messages with history
        messages = [{"role": "system", "content": system_content}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_content})

        for attempt in range(self.max_retries + 1):
            try:
                response = await chat_async(
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )

                return HandlerResult(
                    content=response["content"],
                    citations=[],  # No citations for conversational
                    metadata={
                        "handler": self.get_name(),
                        "latency_ms": (time.perf_counter() - t0) * 1000,
                        "classification": classification.to_dict(),
                    }
                )

            except Exception as e:
                if attempt == self.max_retries:
                    return HandlerResult(
                        content="Xin lỗi, tôi không thể trả lời ngay lúc này.",
                        citations=[],
                        metadata={
                            "handler": self.get_name(),
                            "error": str(e),
                            "latency_ms": (time.perf_counter() - t0) * 1000,
                        },
                        status="error",
                        error=str(e)
                    )

        # Should not reach here
        return HandlerResult(
            content="Xin lỗi, đã xảy ra lỗi không xác định.",
            citations=[],
            metadata={"handler": self.get_name()},
            status="error"
        )

    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None
    ) -> AsyncIterator[dict]:
        """
        Execute conversational query with streaming response.

        Args:
            query: User query string
            user_id: User ID (not used for conversational)
            classification: Pre-classified intent (must be CONVERSATIONAL)
            context: Additional context (conversation history, etc.)

        Yields:
            Dict chunks with type: "thinking", "content", "metadata", "done"
        """
        if classification.intent != Intent.CONVERSATIONAL:
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": f"ConversationalHandler cannot handle intent: {classification.intent}",
                    "handler": self.get_name(),
                }
            }
            return

        t0 = time.perf_counter()
        conversation_history = context.get("conversation_history") if context else None

        system_content = CONVERSATIONAL_SYSTEM_PROMPT
        user_content = CONVERSATIONAL_USER_PROMPT.format(query=query)

        # Build messages with history
        messages = [{"role": "system", "content": system_content}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_content})

        try:
            content_chunk_count = 0
            logger.debug(f"[CONVERSATIONAL STREAM] Starting stream")

            # Apply post-processing to separate thinking from content
            raw_stream = chat_async_stream(
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            async for processed_chunk in stream_with_thinking_separation(raw_stream):
                chunk_type = processed_chunk.get("type")
                chunk_text = processed_chunk.get("text", "")

                if not chunk_text:
                    continue

                content_chunk_count += 1
                if content_chunk_count <= 3 or content_chunk_count % 10 == 0:
                    logger.debug(f"[CONVERSATIONAL STREAM] {chunk_type.upper()} chunk #{content_chunk_count}: {len(chunk_text)} chars")

                # Yield thinking chunks (for UI display in thinking block)
                if chunk_type == "thinking":
                    yield {"type": "thinking", "data": {"text": chunk_text}}
                # Yield content chunks (actual answer)
                elif chunk_type == "content":
                    yield {"type": "content", "data": {"text": chunk_text}}

            logger.debug(f"[CONVERSATIONAL STREAM] Completed: {content_chunk_count} chunks")

            yield {
                "type": "metadata",
                "data": {
                    "status": "conversational",
                    "handler": self.get_name(),
                    "latency_ms": (time.perf_counter() - t0) * 1000,
                },
            }

        except Exception as e:
            logger.error(f"ConversationalHandler stream error: {e}")
            yield {
                "type": "content",
                "data": {"text": "Xin lỗi, tôi không thể trả lời ngay lúc này."},
            }
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": str(e),
                    "handler": self.get_name(),
                },
            }

    def get_config(self) -> HandlerConfig:
        """Get handler configuration."""
        return self.config

    def get_name(self) -> str:
        """Get handler name."""
        return "ConversationalHandler"
