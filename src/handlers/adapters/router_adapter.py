"""
Router to Handler adapter for backward compatibility.

Maintains compatibility with existing BaseRouter interface during migration.
"""

import time
from typing import Any, AsyncIterator
from uuid import UUID

from src.agents.routers.base import BaseRouter
from src.protocols.classification import ClassificationResult, Intent
from src.protocols.handlers import HandlerResult, HandlerConfig
from src.abc.handlers import QueryHandlerABC
from src.agents.routers.classifier import QueryClassifier


class RouterToHandlerAdapter(QueryHandlerABC):
    """
    Adapts BaseRouter to QueryHandler protocol.

    Wraps existing BaseRouter implementations to work with new Handler interface.
    Enables zero-downtime migration with feature flags.

    Example:
        >>> router = RAGRouter()
        >>> adapter = RouterToHandlerAdapter(router, QueryClassifier())
        >>> result = await adapter.handle("query", "user123", classification)
    """

    def __init__(
        self,
        router: BaseRouter,
        classifier: QueryClassifier | None = None
    ):
        """
        Initialize router adapter.

        Args:
            router: Existing BaseRouter implementation
            classifier: Optional classifier for classification (if not pre-classified)
        """
        self.router = router
        self.classifier = classifier
        self.config = HandlerConfig()  # Default config

    def can_handle(self, classification: ClassificationResult) -> bool:
        """
        Check if router can handle the classification.

        Delegates to router.can_handle() with confidence check.

        Args:
            classification: Pre-classified intent and metadata

        Returns:
            True if router confidence >= 0.5
        """
        # If classification has high confidence, router can handle
        if classification.confidence >= 0.5:
            return True

        # Optionally use internal classifier to check
        if self.classifier:
            return True

        return False

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None
    ) -> HandlerResult:
        """
        Execute query using router.handle().

        Args:
            query: User query string
            user_id: User ID
            classification: Pre-classified intent and metadata
            context: Additional context (conversation history, etc.)

        Returns:
            HandlerResult with converted router response
        """
        t0 = time.perf_counter()
        conversation_history = context.get("conversation_history") if context else None

        try:
            # Call old router interface
            result = await self.router.handle(query, user_id, conversation_history)

            # Convert to HandlerResult format
            return HandlerResult(
                content=result.get("content", ""),
                citations=self._convert_citations(result.get("citations", [])),
                metadata={
                    "handler": self.get_name(),
                    "router": self.router.get_name(),
                    "latency_ms": result.get("latency_ms", (time.perf_counter() - t0) * 1000),
                    "classification": classification.to_dict(),
                    "adapter": True,
                }
            )

        except Exception as e:
            return HandlerResult(
                content=f"Error in router adapter: {str(e)}",
                citations=[],
                metadata={
                    "handler": self.get_name(),
                    "router": self.router.get_name(),
                    "error": str(e),
                    "latency_ms": (time.perf_counter() - t0) * 1000,
                },
                status="error",
                error=str(e)
            )

    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None
    ) -> AsyncIterator[dict]:
        """
        Execute query using router.handle_stream().

        Args:
            query: User query string
            user_id: User ID
            classification: Pre-classified intent and metadata
            context: Additional context

        Yields:
            Dict chunks from router streaming
        """
        conversation_history = context.get("conversation_history") if context else None

        try:
            async for chunk in self.router.handle_stream(query, user_id, conversation_history):
                yield chunk

        except Exception as e:
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": str(e),
                    "handler": self.get_name(),
                    "router": self.router.get_name(),
                }
            }

    def get_config(self) -> HandlerConfig:
        """Get handler configuration."""
        return self.config

    def get_name(self) -> str:
        """Get handler name (includes router name)."""
        return f"RouterAdapter({self.router.get_name()})"

    def _convert_citations(self, raw_citations: list) -> list:
        """Convert raw citations to HandlerResult format."""
        from src.protocols.handlers import Citation

        citations = []

        for cite in raw_citations:
            if isinstance(cite, dict):
                citations.append(Citation(
                    filename=cite.get("filename", ""),
                    text=cite.get("text", ""),
                    page=cite.get("page"),
                    confidence=cite.get("confidence", 1.0),
                ))
            elif hasattr(cite, "to_dict"):
                citations.append(cite)

        return citations


class HandlerToRouterAdapter(BaseRouter):
    """
    Adapts QueryHandlerABC to BaseRouter protocol.

    Wraps new QueryHandler implementations to work with old Router interface.
    Enables gradual migration from routers to handlers.

    Example:
        >>> handler = RAGHandler()
        >>> adapter = HandlerToRouterAdapter(handler, QueryClassifier())
        >>> confidence = await adapter.can_handle("query")
        >>> result = await adapter.handle("query", "user123")
    """

    def __init__(
        self,
        handler: QueryHandlerABC,
        classifier: QueryClassifier
    ):
        """
        Initialize handler adapter.

        Args:
            handler: New QueryHandler implementation
            classifier: Classifier for intent detection
        """
        self.handler = handler
        self.classifier = classifier

    async def can_handle(self, query: str) -> float:
        """
        Check if handler can handle the query.

        Uses classifier to detect intent and returns confidence.

        Args:
            query: User query string

        Returns:
            Confidence score 0.0-1.0
        """
        # Classify query
        classification = await self.classifier.classify(query)

        # Check if handler can handle this classification
        if self.handler.can_handle(classification):
            return classification.confidence

        return 0.0

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        conversation_history: list[dict] | None = None
    ) -> dict[str, Any]:
        """
        Execute query using handler.

        Args:
            query: User query string
            user_id: User ID
            conversation_history: Optional conversation history

        Returns:
            Response dict in router format
        """
        # Classify query
        classification = await self.classifier.classify(query)

        # Build context
        context = {"conversation_history": conversation_history} if conversation_history else None

        # Call handler
        result = await self.handler.handle(query, user_id, classification, context)

        # Convert to router format
        return {
            "content": result.content,
            "citations": [cite.to_dict() for cite in result.citations],
            "sources": [],  # Deprecated in handlers
            "metadata": {
                **result.metadata,
                "router": self.get_name(),
                "adapter": True,
            },
            "latency_ms": result.get_latency_ms() or 0,
            "retrieval_history": result.metadata.get("retrieval_history", []),
        }

    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
        conversation_history: list[dict] | None = None
    ) -> AsyncIterator[dict]:
        """
        Execute query using handler with streaming.

        Args:
            query: User query string
            user_id: User ID
            conversation_history: Optional conversation history

        Yields:
            Dict chunks in router format
        """
        # Classify query
        classification = await self.classifier.classify(query)

        # Build context
        context = {"conversation_history": conversation_history} if conversation_history else None

        # Stream from handler
        async for chunk in self.handler.handle_stream(query, user_id, classification, context):
            yield chunk

    def get_name(self) -> str:
        """Get router name (includes handler name)."""
        return f"HandlerAdapter({self.handler.get_name()})"
