"""
Interface definitions for query handlers using Abstract Base Classes (ABC).

This module provides ABC-based handler interfaces for nominal type checking.
These ABCs define the interface contract that all query handler implementations must follow.

This module now contains BOTH ABC interfaces AND data models (Citation, HandlerResult, HandlerConfig).
Previously, data models were in src.protocols.handlers - now unified in ABC-only architecture.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Any
from dataclasses import dataclass, field
from uuid import UUID

# Import from unified interfaces module
from src.shared.kernel.interfaces.classification import ClassificationResult


__all__ = [
    # Data models
    "Citation",
    "HandlerResult",
    "HandlerConfig",
    # ABC interfaces
    "QueryHandlerBase",
]


# ============================================================================
# DATA MODELS (formerly in src.protocols.handlers)
# ============================================================================

@dataclass(frozen=True)
class Citation:
    """
    Citation for sourced information.

    Attributes:
        filename: Source document filename
        page: Page number (if applicable)
        text: Excerpt from the source
        url: URL to the source (if applicable)
        confidence: Confidence score for the citation
        metadata: Additional metadata

    Example:
        >>> citation = Citation(
        ...     filename="contract.pdf",
        ...     page=1,
        ...     text="The agreement term is 12 months...",
        ...     confidence=0.95
        ... )
    """

    filename: str
    text: str
    page: int | None = None
    url: str | None = None
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "filename": self.filename,
            "page": self.page,
            "text": self.text,
            "url": self.url,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class HandlerResult:
    """
    Result of query handler execution.

    Attributes:
        content: Main response content
        citations: List of citations for sourced information
        metadata: Handler metadata (latency, docs_retrieved, etc.)
        conversation_id: Conversation ID for context tracking
        message_id: Message ID for deduplication
        status: Execution status (success, error, etc.)
        error: Error message if status is error

    Example:
        >>> result = HandlerResult(
        ...     content="Based on the contract...",
        ...     citations=[Citation(filename="contract.pdf", page=1, text="...")],
        ...     metadata={"handler": "RAGHandler", "docs_retrieved": 5, "latency_ms": 1234}
        ... )
    """

    content: str
    citations: list[Citation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    conversation_id: str | None = None
    message_id: str | None = None
    status: str = "success"
    error: str | None = None

    def __post_init__(self):
        """Validate handler result."""
        if self.status == "error" and not self.error:
            raise ValueError("Error status requires error message")

    def is_success(self) -> bool:
        """Check if handler execution was successful."""
        return self.status == "success"

    def is_error(self) -> bool:
        """Check if handler execution failed."""
        return self.status == "error"

    def get_latency_ms(self) -> float | None:
        """Get execution latency from metadata."""
        return self.metadata.get("latency_ms")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "citations": [c.to_dict() for c in self.citations],
            "metadata": self.metadata,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "status": self.status,
            "error": self.error,
        }


@dataclass
class HandlerConfig:
    """
    Configuration for query handlers.

    Attributes:
        max_retrieved_docs: Maximum number of documents to retrieve (RAG handlers)
        max_tokens: Maximum tokens for LLM generation
        temperature: LLM temperature for generation
        streaming_enabled: Whether streaming is supported
        timeout_ms: Execution timeout in milliseconds
        retry_count: Number of retries on failure
        metadata: Additional handler-specific configuration

    Example:
        >>> config = HandlerConfig(
        ...     max_retrieved_docs=5,
        ...     max_tokens=2000,
        ...     temperature=0.7,
        ...     streaming_enabled=True
        ... )
    """

    max_retrieved_docs: int = 5
    max_tokens: int = 2000
    temperature: float = 0.7
    streaming_enabled: bool = True
    timeout_ms: int = 30000
    retry_count: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "max_retrieved_docs": self.max_retrieved_docs,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "streaming_enabled": self.streaming_enabled,
            "timeout_ms": self.timeout_ms,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }


# ============================================================================
# ABC INTERFACES
# ============================================================================

class QueryHandlerBase(ABC):
    """
    Abstract base class for query execution handlers.

    This ABC defines the interface that all query handler implementations must implement.
    Handlers receive pre-classified queries and execute domain-specific logic.
    No classification logic should be in handlers (SRP compliance).

    Example:
        >>> from interfaces.handlers import QueryHandlerBase
        >>>
        >>> class MyHandler(QueryHandlerBase):
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
        classification: ClassificationResult,
        context: dict[str, Any] | None = None
    ) -> HandlerResult:
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
        classification: ClassificationResult,
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

    @abstractmethod
    def can_handle(self, classification: ClassificationResult) -> bool:
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
    def get_config(self) -> HandlerConfig:
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
