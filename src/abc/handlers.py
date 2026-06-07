"""
ABC (Abstract Base Class) interfaces for query handlers.

This module provides ABC versions of handler protocols for nominal type checking.
These ABCs are designed to be equivalent to the Protocol interfaces in src.protocols.handlers.

While Protocols enable structural subtyping (duck typing), ABCs enable nominal subtyping
(explicit inheritance). Both approaches are valid - choose based on your needs:

- Use Protocols (src.protocols.handlers) for structural typing - any class with matching methods works
- Use ABCs (src.abc.handlers) for nominal typing - explicit inheritance required

These ABCs match QueryHandler protocol exactly for full compatibility.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, AsyncIterator, Any
from uuid import UUID

if TYPE_CHECKING:
    from src.protocols.handlers import (
        HandlerResult,
        HandlerConfig,
        ClassificationResult,
    )


class QueryHandlerABC(ABC):
    """
    Abstract base class for query execution handlers.

    This ABC defines the nominal interface that all query handlers must implement.
    It matches the QueryHandler Protocol exactly for full compatibility.

    Handlers receive pre-classified queries and execute domain-specific logic.
    No classification logic should be in handlers (SRP compliance).

    Example:
        >>> from src.abc.handlers import QueryHandlerABC
        >>>
        >>> class MyHandler(QueryHandlerABC):
        ...     def __init__(self, config: HandlerConfig):
        ...         self.config = config
        ...
        ...     async def handle(self, query, user_id, classification, context=None):
        ...         return HandlerResult(content="Response")
        ...
        ...     async def handle_stream(self, query, user_id, classification, context=None):
        ...         yield {"type": "content", "data": {"text": "..."}}
        ...
        ...     def can_handle(self, classification):
        ...         return classification.intent == Intent.RAG
        ...
        ...     def get_config(self):
        ...         return self.config
        ...
        ...     def get_name(self):
        ...         return "MyHandler"
    """

    @abstractmethod
    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: "ClassificationResult",
        context: dict[str, Any] | None = None
    ) -> "HandlerResult":
        """
        Execute query with known classification (non-streaming).

        Args:
            query: User query string
            user_id: User ID for personalization
            classification: Pre-classified intent and metadata
            context: Additional context (conversation history, user preferences, etc.)

        Returns:
            HandlerResult with content, citations, and metadata

        Raises:
            ValueError: If query is empty or classification is invalid
            TimeoutError: If execution exceeds timeout
            Exception: If handler execution fails

        Example:
            >>> result = await handler.handle("hỏi về contract.pdf", "user123", classification)
            >>> assert result.content
            >>> assert result.is_success()
        """
        pass

    @abstractmethod
    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
        classification: "ClassificationResult",
        context: dict[str, Any] | None = None
    ) -> AsyncIterator[dict]:
        """
        Execute query with streaming response.

        Yields dictionaries with SSE-compatible format:
        - {"type": "content", "data": {"text": "..."}}
        - {"type": "metadata", "data": {"citations": [...]}}
        - {"type": "done"}

        Args:
            query: User query string
            user_id: User ID for personalization
            classification: Pre-classified intent and metadata
            context: Additional context

        Yields:
            Dict chunks with type and data fields

        Example:
            >>> async for chunk in handler.handle_stream("query", "user123", classification):
            ...     if chunk["type"] == "content":
            ...         print(chunk["data"]["text"])
        """
        pass
        yield  # Make this a generator function

    @abstractmethod
    def can_handle(self, classification: "ClassificationResult") -> bool:
        """
        Check if handler can handle the given classification.

        This is used for handler routing/dispatch.

        Args:
            classification: Pre-classified intent and metadata

        Returns:
            True if handler can handle this intent, False otherwise

        Example:
            >>> if handler.can_handle(classification):
            ...     result = await handler.handle(query, user_id, classification)
        """
        pass

    @abstractmethod
    def get_config(self) -> "HandlerConfig":
        """
        Get handler configuration.

        Returns:
            HandlerConfig with handler settings

        Example:
            >>> config = handler.get_config()
            >>> assert config.max_retrieved_docs == 5
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get handler name for telemetry/logging.

        Returns:
            Handler name (e.g., "RAGHandler", "ConversationalHandler")

        Example:
            >>> name = handler.get_name()
            >>> print(f"Using handler: {name}")
        """
        pass
