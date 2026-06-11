"""
Conversational handler - Infrastructure layer adapter for direct LLM chat.

Migrated from src/handlers/conversational.py to modules/chat/infrastructure/handlers/.
Handles conversational queries with pre-classified CONVERSATIONAL intent.
No retrieval, just direct LLM chat with thinking separation.

Delegates message building to ConversationService (domain layer),
keeping this handler focused on LLM orchestration.
"""

import time
from loguru import logger
from typing import Any, AsyncIterator

from src.shared.kernel.interfaces.classification import ClassificationResult, Intent
from src.shared.kernel.interfaces.handlers import QueryHandlerBase, HandlerResult, HandlerConfig

from src.modules.chat.domain.services import ConversationService, ConversationContext

# Import from infrastructure and shared modules
from src.shared.infrastructure.llm.client import chat_async, chat_async_stream
from src.shared.utils.postprocess import stream_with_thinking_separation
# Import from chat domain prompts
from src.modules.chat.domain.prompts.conversational import CONVERSATIONAL_SYSTEM_PROMPT, CONVERSATIONAL_USER_PROMPT


class ConversationalHandler(QueryHandlerBase):
    """Handler for conversational queries (greetings, casual chat).

    Receives pre-classified CONVERSATIONAL queries and executes direct LLM chat.
    No retrieval, no classification logic (SRP compliance).

    Delegates message building to ConversationService (domain layer)
    and LLM calls to agents.llm (infrastructure).
    """

    def __init__(
        self,
        config: HandlerConfig | None = None,
        max_retries: int = 2,
    ):
        """Initialize conversational handler.

        Args:
            config: Optional handler configuration
            max_retries: Max retry attempts for LLM calls
        """
        self.config = config or HandlerConfig()
        self.max_retries = max_retries
        self._conversation_service = ConversationService()

    def can_handle(self, classification: ClassificationResult) -> bool:
        """Check if handler can handle the classification.

        Args:
            classification: Pre-classified intent and metadata

        Returns:
            True if intent is CONVERSATIONAL
        """
        return classification.intent == Intent.CONVERSATIONAL

    async def handle(
        self,
        query: str,
        user_id: Any,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None,
    ) -> HandlerResult:
        """Execute conversational query (non-streaming).

        Args:
            query: User query string
            user_id: User ID (not used for conversational)
            classification: Pre-classified intent (must be CONVERSATIONAL)
            context: Additional context (conversation history, etc.)

        Returns:
            HandlerResult with content and metadata

        Raises:
            ValueError: If classification intent is not CONVERSATIONAL
        """
        if classification.intent != Intent.CONVERSATIONAL:
            raise ValueError(
                f"ConversationalHandler cannot handle intent: {classification.intent}"
            )

        logger.info(
            f"🚀 <yellow>[CONVERSATIONAL FLOW]</yellow> Starting conversational handler. "
            f"Query: \"{query[:50] + '...' if len(query) > 50 else query}\""
        )
        t0 = time.perf_counter()
        conversation_history = context.get("conversation_history") if context else None

        # Build messages using domain service
        conv_context = ConversationContext(
            query=query,
            conversation_history=conversation_history or [],
            system_prompt=CONVERSATIONAL_SYSTEM_PROMPT,
            user_prompt_template=CONVERSATIONAL_USER_PROMPT,
        )
        messages = self._conversation_service.build_messages(conv_context)

        for attempt in range(self.max_retries + 1):
            try:
                response = await chat_async(
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )

                latency_ms = (time.perf_counter() - t0) * 1000
                logger.info(
                    f"✅ <green>[CONVERSATIONAL FLOW COMPLETED]</green> Conversational response generated. "
                    f"Content size: {len(response['content'])} chars, Latency: <yellow>{latency_ms:.2f}ms</yellow>"
                )

                return HandlerResult(
                    content=response["content"],
                    citations=[],
                    metadata={
                        "handler": self.get_name(),
                        "latency_ms": latency_ms,
                        "classification": classification.to_dict(),
                    },
                )

            except Exception as e:
                logger.warning(f"⚠️  [CONVERSATIONAL attempt {attempt}] LLM call failed: {e}")
                if attempt == self.max_retries:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    logger.error(
                        f"❌ <red>[CONVERSATIONAL FLOW ERROR]</red> Conversational execution failed. "
                        f"Latency: <yellow>{latency_ms:.2f}ms</yellow>"
                    )
                    return HandlerResult(
                        content="Xin lỗi, tôi không thể trả lời ngay lúc này.",
                        citations=[],
                        metadata={
                            "handler": self.get_name(),
                            "error": str(e),
                            "latency_ms": latency_ms,
                        },
                        status="error",
                        error=str(e),
                    )

        # Should not reach here
        return HandlerResult(
            content="Xin lỗi, đã xảy ra lỗi không xác định.",
            citations=[],
            metadata={"handler": self.get_name()},
            status="error",
        )

    async def handle_stream(
        self,
        query: str,
        user_id: Any,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict]:
        """Execute conversational query with streaming response.

        Args:
            query: User query string
            user_id: User ID (not used for conversational)
            classification: Pre-classified intent (must be CONVERSATIONAL)
            context: Additional context (conversation history, etc.)

        Yields:
            Dict chunks with type: thinking, content, metadata, done
        """
        if classification.intent != Intent.CONVERSATIONAL:
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": f"ConversationalHandler cannot handle intent: {classification.intent}",
                    "handler": self.get_name(),
                },
            }
            return

        logger.info(
            f"🚀 <yellow>[CONVERSATIONAL STREAM FLOW]</yellow> Starting conversational stream. "
            f"Query: \"{query[:50] + '...' if len(query) > 50 else query}\""
        )
        t0 = time.perf_counter()
        conversation_history = context.get("conversation_history") if context else None

        # Build messages using domain service
        conv_context = ConversationContext(
            query=query,
            conversation_history=conversation_history or [],
            system_prompt=CONVERSATIONAL_SYSTEM_PROMPT,
            user_prompt_template=CONVERSATIONAL_USER_PROMPT,
        )
        messages = self._conversation_service.build_messages(conv_context)

        try:
            content_chunk_count = 0
            logger.debug("[CONVERSATIONAL STREAM] Starting stream")

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
                    logger.debug(
                        f"[CONVERSATIONAL STREAM] {chunk_type.upper()} "
                        f"chunk #{content_chunk_count}: {len(chunk_text)} chars"
                    )

                # Yield thinking chunks (for UI display in thinking block)
                if chunk_type == "thinking":
                    yield {"type": "thinking", "data": {"text": chunk_text}}
                # Yield content chunks (actual answer)
                elif chunk_type == "content":
                    yield {"type": "content", "data": {"text": chunk_text}}

            latency_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                f"✅ <green>[CONVERSATIONAL STREAM COMPLETED]</green> Generated stream. "
                f"Chunks: {content_chunk_count}, Latency: <yellow>{latency_ms:.2f}ms</yellow>"
            )

            yield {
                "type": "metadata",
                "data": {
                    "status": "conversational",
                    "handler": self.get_name(),
                    "latency_ms": latency_ms,
                },
            }

        except Exception as e:
            logger.error(f"❌ <red>[CONVERSATIONAL STREAM ERROR]</red> ConversationalHandler stream error: {e}")
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


__all__ = ["ConversationalHandler"]