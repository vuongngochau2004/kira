"""
Chat use case - Application-level orchestration for chat queries.

Delegates workflow routing to ChatGraph:
1. Classification node determines user intent
2. Dispatch node selects the conversational or RAG handler
3. Handler result is converted to the application DTO
"""

from loguru import logger
import time
from typing import Any

from src.shared.ports.classification import Intent
from src.shared.ports.handlers import QueryHandlerBase

from src.modules.chat.application.dto import ChatQuery, ChatResult, StreamChunk
from src.modules.chat.application.graph import ChatGraph


class ChatUseCase:
    """Use case for processing chat queries with intent-based routing.

    Orchestrates the full chat pipeline:
    - Receives a ChatQuery (message, user_id, context)
    - Classifies intent using injected classifier
    - Routes to appropriate handler (RAG or Conversational)
    - Returns a ChatResult with response, citations, and metadata

    ChatGraph keeps the application-level routing workflow explicit and testable.

    Args:
        classifier: Strategy for classifying query intent
        handlers: Dict mapping Intent to QueryHandlerBase implementation
    """

    def __init__(
        self,
        classifier: Any,  # ClassificationStrategyBase (Protocol in future)
        handlers: dict[Intent, QueryHandlerBase],
    ):
        """Initialize ChatUseCase with classifier and handler registry.

        Args:
            classifier: Classification strategy (CompositeClassifier recommended).
                         Should implement classify(query, user_id) -> ClassificationResult
            handlers: Mapping of Intent -> QueryHandlerBase implementation.
                     Must include at least RAG and CONVERSATIONAL handlers.
        """
        self.classifier = classifier
        self.handlers = handlers
        self.graph = ChatGraph(classifier=classifier, handlers=handlers)

    async def execute(self, query: ChatQuery) -> ChatResult:
        """Execute a chat query (non-streaming).

        Args:
            query: ChatQuery with message, user_id, and optional context

        Returns:
            ChatResult with content, citations, and metadata

        Raises:
            ValueError: If no handler found for classified intent
        """
        t0 = time.perf_counter()
        conv_id = query.context.get("conversation_id") if query.context else None

        logger.info(
            f"📥 <blue>[USER REQUEST]</blue> user_id='{query.user_id}', "
            f"conversation_id='{conv_id or 'None'}'"
        )
        logger.info(f"💬 <blue>[MESSAGE]</blue> \"{query.message}\"")

        try:
            state = await self.graph.run(query)
            classification = state["classification"]
            result = state["handler_result"]

            latency_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                f"✅ <green>[COMPLETED]</green> Query execution finished. "
                f"Content size: {len(result.content)} chars, "
                f"Citations count: {len(result.citations)}, "
                f"Latency: <yellow>{latency_ms:.2f}ms</yellow>"
            )

            return ChatResult.from_handler_result(
                result=result,
                classification=classification,
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.error(
                f"❌ <red>[ERROR]</red> ChatUseCase execute failed: {e}. "
                f"Latency: <yellow>{latency_ms:.2f}ms</yellow>",
                exc_info=True,
            )
            return ChatResult(
                content="Có lỗi xảy ra khi xử lý câu hỏi.",
                citations=[],
                metadata={
                    "handler": "ChatUseCase",
                    "error": str(e),
                    "latency_ms": latency_ms,
                },
                status="error",
                error=str(e),
            )

    async def execute_stream(self, query: ChatQuery):
        """Execute a chat query with streaming response.

        Args:
            query: ChatQuery with message, user_id, and optional context

        Yields:
            StreamChunk dicts with type: routing, retrieval, content, thinking, metadata, done
        """
        t0 = time.perf_counter()
        conv_id = query.context.get("conversation_id") if query.context else None

        logger.info(
            f"📥 <blue>[USER REQUEST STREAM]</blue> user_id='{query.user_id}', "
            f"conversation_id='{conv_id or 'None'}'"
        )
        logger.info(f"💬 <blue>[MESSAGE]</blue> \"{query.message}\"")

        try:
            async for chunk in self.graph.run_stream(query):
                yield chunk

            latency_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                f"✅ <green>[STREAM COMPLETED]</green> Streaming completed. "
                f"Latency: <yellow>{latency_ms:.2f}ms</yellow>"
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.error(
                f"❌ <red>[STREAM ERROR]</red> ChatUseCase stream failed: {e}. "
                f"Latency: <yellow>{latency_ms:.2f}ms</yellow>",
                exc_info=True,
            )
            yield StreamChunk.error(str(e))


__all__ = ["ChatUseCase"]
