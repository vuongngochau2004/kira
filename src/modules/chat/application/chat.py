"""
Chat use case - Application-level orchestration for chat queries.

Orchestrates the full chat pipeline:
1. Classify query intent (RAG vs conversational)
2. Route to appropriate handler
3. Return structured result

Replaces the old OrchestratorAgent/RouterRegistry pattern with
a clean use case that follows SOLID principles.
"""

from loguru import logger
import time
from uuid import UUID
from typing import Any

from src.shared.kernel.interfaces.classification import Intent, ClassificationResult
from src.shared.kernel.interfaces.handlers import QueryHandlerBase, HandlerResult, HandlerConfig

from src.modules.chat.application.dto import ChatQuery, ChatResult, StreamChunk


class ChatUseCase:
    """Use case for processing chat queries with intent-based routing.

    Orchestrates the full chat pipeline:
    - Receives a ChatQuery (message, user_id, context)
    - Classifies intent using injected classifier
    - Routes to appropriate handler (RAG or Conversational)
    - Returns a ChatResult with response, citations, and metadata

    This use case replaces the old OrchestratorAgent pattern with
    a cleaner, testable application service.

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
            # Step 1: Classify intent
            classification = await self._classify(query)

            # Step 2: Select handler
            handler = self._select_handler(classification)
            handler_name = handler.get_name() if hasattr(handler, "get_name") else handler.__class__.__name__
            logger.info(
                f"🎯 <magenta>[STEP 2/3: ROUTING]</magenta> Selected handler <yellow>{handler_name}</yellow> "
                f"for intent '<magenta>{classification.intent.value}</magenta>'"
            )

            # Step 3: Execute handler
            context = query.context or {}
            if query.conversation_history:
                context["conversation_history"] = query.conversation_history

            logger.info(f"🚀 <yellow>[STEP 3/3: EXECUTION]</yellow> Running handler <green>{handler_name}</green>...")
            result = await handler.handle(
                query=query.message,
                user_id=query.user_id,
                classification=classification,
                context=context if context else None,
            )

            latency_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                f"✅ <green>[COMPLETED]</green> Query execution finished. "
                f"Content size: {len(result.content)} chars, "
                f"Citations count: {len(result.citations)}, "
                f"Latency: <yellow>{latency_ms:.2f}ms</yellow>"
            )

            # Step 4: Convert to ChatResult
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
            # Step 1: Classify intent
            classification = await self._classify(query)

            # Step 2: Yield routing decision
            handler_name = self._get_handler_name(classification.intent)
            yield StreamChunk.routing(
                router_name=handler_name,
                intent=classification.intent.value,
                confidence=classification.confidence,
                reasoning=classification.reason,
            )

            # Step 3: Select handler
            handler = self._select_handler(classification)
            logger.info(
                f"🎯 <magenta>[STEP 2/3: ROUTING]</magenta> Selected streaming handler <yellow>{handler_name}</yellow> "
                f"for intent '<magenta>{classification.intent.value}</magenta>'"
            )

            # Step 4: Stream from handler
            context = query.context or {}
            if query.conversation_history:
                context["conversation_history"] = query.conversation_history

            logger.info(f"🚀 <yellow>[STEP 3/3: EXECUTION]</yellow> Streaming using <green>{handler_name}</green>...")
            async for chunk in handler.handle_stream(
                query=query.message,
                user_id=query.user_id,
                classification=classification,
                context=context if context else None,
            ):
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

    async def _classify(self, query: ChatQuery) -> ClassificationResult:
        """Classify query intent using injected classifier.

        Args:
            query: ChatQuery to classify

        Returns:
            ClassificationResult with intent and confidence
        """
        logger.info("🔍 <cyan>[STEP 1/3: CLASSIFICATION]</cyan> Classifying user query intent...")
        try:
            result = await self.classifier.classify(
                query=query.message,
                user_id=str(query.user_id),
            )
            logger.info(
                f"📊 <cyan>[CLASSIFICATION RESULT]</cyan> Intent: <magenta>{result.intent.value}</magenta>, "
                f"Confidence: <yellow>{result.confidence:.2f}</yellow>, "
                f"Reason: {result.reason}"
            )
            return result
        except Exception as e:
            logger.warning(
                f"⚠️  <yellow>[CLASSIFICATION FALLBACK]</yellow> Classification failed: {e}. "
                f"Defaulting to RAG intent."
            )
            # Default to RAG on classification failure
            return ClassificationResult(
                intent=Intent.RAG,
                confidence=0.5,
                reason=f"Classification fallback: {e}",
            )

    def _select_handler(self, classification: ClassificationResult) -> QueryHandlerBase:
        """Select handler based on classified intent.

        Args:
            classification: Classification result with intent

        Returns:
            Appropriate handler for the intent

        Raises:
            ValueError: If no handler registered for the intent
        """
        handler = self.handlers.get(classification.intent)
        if handler is None:
            # Fallback to RAG handler for unknown intents
            handler = self.handlers.get(Intent.RAG)

        if handler is None:
            raise ValueError(
                f"No handler registered for intent: {classification.intent}. "
                f"Available handlers: {list(self.handlers.keys())}"
            )

        return handler

    def _get_handler_name(self, intent: Intent) -> str:
        """Get human-readable handler name for routing chunk.

        Args:
            intent: Classified intent

        Returns:
            Handler name string
        """
        handler = self.handlers.get(intent)
        if handler and hasattr(handler, "get_name"):
            return handler.get_name()
        return f"{intent.value}Handler"


__all__ = ["ChatUseCase"]