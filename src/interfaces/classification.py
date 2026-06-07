"""
Interface definitions for classification using Abstract Base Classes (ABC).

This module provides ABC-based classification interfaces for formal inheritance.
These ABCs enable compile-time type checking, explicit interface contracts, and better IDE support.

This module now contains BOTH ABC interfaces AND data models (Intent, ClassificationResult).
Previously, data models were in src.protocols.classification - now unified in ABC-only architecture.

Example:
    >>> from src.interfaces.classification import ClassificationCacheBase, ClassificationStrategyBase
    >>>
    >>> class MyCache(ClassificationCacheBase):
    ...     async def get(self, key: str) -> ClassificationResult | None:
    ...         return self._cache.get(key)
    >>>
    >>> class MyStrategy(ClassificationStrategyBase):
    ...     async def classify(self, query: str, user_id: str, context: dict | None = None) -> ClassificationResult:
    ...         return ClassificationResult(intent=Intent.RAG, confidence=0.9)
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID


__all__ = [
    # Data models
    "Intent",
    "ClassificationResult",
    # ABC interfaces
    "ClassificationCacheBase",
    "ClassificationStrategyBase",
]


# ============================================================================
# DATA MODELS (formerly in src.protocols.classification)
# ============================================================================

class Intent(str, Enum):
    """
    Query intent enumeration.

    Represents the different types of user queries in the RAG system:
    - RAG: Document retrieval and generation
    - CONVERSATIONAL: Direct chat without retrieval
    - DRAFTING: Content creation (future)
    - SEMANTIC: Semantic routing (future)
    """

    RAG = "rag"
    CONVERSATIONAL = "conversational"
    DRAFTING = "drafting"
    SEMANTIC = "semantic"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ClassificationResult:
    """
    Result of query classification.

    Attributes:
        intent: The detected intent (RAG, CONVERSATIONAL, etc.)
        confidence: Confidence score between 0.0 and 1.0
        reason: Human-readable explanation of the classification
        metadata: Additional metadata for debugging/telemetry
        handler_hint: Optional hint for which handler to use

    Example:
        >>> result = ClassificationResult(
        ...     intent=Intent.RAG,
        ...     confidence=0.95,
        ...     reason="File keyword detected: 'tài liệu'",
        ...     metadata={"strategy": "keyword", "matched_files": ["contract.pdf"]}
        ... )
    """

    intent: Intent
    confidence: float
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    handler_hint: str | None = None

    def __post_init__(self):
        """Validate classification result."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"ClassificationResult.confidence must be between 0.0 and 1.0 (inclusive), "
                f"got {self.confidence}. This ensures proper confidence thresholding."
            )

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if classification has high confidence."""
        return self.confidence >= threshold

    def is_rag_intent(self) -> bool:
        """Check if intent is RAG."""
        return self.intent == Intent.RAG

    def is_conversational_intent(self) -> bool:
        """Check if intent is CONVERSATIONAL."""
        return self.intent == Intent.CONVERSATIONAL

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "metadata": self.metadata,
            "handler_hint": self.handler_hint,
        }


# ============================================================================
# ABC INTERFACES
# ============================================================================

class ClassificationCacheBase(ABC):
    """
    Abstract base class for classification result caching.

    This ABC defines the interface for classification cache implementations.
    Implementations can use LRU cache, Redis, or other caching mechanisms.

    Example:
        >>> class LRUCache(ClassificationCacheBase):
        ...     def __init__(self):
        ...         self._cache = {}
        ...
        ...     async def get(self, key: str) -> ClassificationResult | None:
        ...         return self._cache.get(key)
        ...
        ...     async def set(self, key: str, value: ClassificationResult, ttl: int | None = None) -> None:
        ...         self._cache[key] = value
    """

    @abstractmethod
    async def get(self, key: str) -> ClassificationResult | None:
        """
        Get cached classification result.

        Args:
            key: Cache key (typically user_id:query_hash)

        Returns:
            ClassificationResult if cached and not expired, None otherwise
        """
        ...

    @abstractmethod
    async def set(
        self,
        key: str,
        value: ClassificationResult,
        ttl: int | None = None
    ) -> None:
        """
        Cache classification result with TTL.

        Args:
            key: Cache key
            value: ClassificationResult to cache
            ttl: Time-to-live in seconds (None for no expiration)
        """
        ...

    @abstractmethod
    async def invalidate(self, key: str) -> None:
        """
        Invalidate cache entry.

        Args:
            key: Cache key to invalidate
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with stats: hit_rate, size, ttl, etc.
        """
        ...


class ClassificationStrategyBase(ABC):
    """
    Abstract base class for classification strategies.

    This ABC defines the interface for classification strategy implementations.
    Implementations should be async and thread-safe.

    Example:
        >>> class KeywordClassifier(ClassificationStrategyBase):
        ...     async def classify(self, query: str, user_id: str, context: dict | None = None) -> ClassificationResult:
        ...         # Fast keyword-based classification
        ...         if "tài liệu" in query.lower():
        ...             return ClassificationResult(intent=Intent.RAG, confidence=0.9, reason="Keyword detected")
        ...         return ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.6, reason="No keywords")
    """

    @abstractmethod
    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        """
        Classify query intent.

        Args:
            query: User query string
            user_id: User ID for personalization and user-scoped logic
            context: Additional context (conversation history, user preferences, etc.)

        Returns:
            ClassificationResult with intent, confidence, and metadata

        Raises:
            ValueError: If query is empty or invalid
            Exception: If classification fails (implementations should handle gracefully)

        Example:
            >>> result = await strategy.classify("hỏi về contract.pdf", "user123")
            >>> assert result.intent == Intent.RAG
            >>> assert result.confidence > 0.8
        """
        ...

    def can_handle(self, query: str, user_id: str | UUID) -> bool:
        """
        Quick synchronous check if strategy can handle the query.

        This is an optional optimization for fast-path filtering.
        Default implementation should return True (always attempt classification).

        Args:
            query: User query string
            user_id: User ID

        Returns:
            True if strategy should attempt classification, False otherwise

        Example:
            >>> if strategy.can_handle(query, user_id):
            ...     result = await strategy.classify(query, user_id)
        """
        return True
