"""
Abstract base classes for classification protocols.

This module provides ABC versions of classification protocols for formal inheritance.
These ABCs match their Protocol counterparts exactly for maximum compatibility.

The ABC versions enable:
- Formal inheritance with @abstractmethod
- Runtime type checking with isinstance()
- Explicit interface contracts
- Better IDE support for inheritance

Example:
    >>> from src.abc.classification import ClassificationCacheABC, ClassificationStrategyABC
    >>>
    >>> class MyCache(ClassificationCacheABC):
    ...     async def get(self, key: str) -> ClassificationResult | None:
    ...         return self._cache.get(key)
    >>>
    >>> class MyStrategy(ClassificationStrategyABC):
    ...     async def classify(self, query: str, user_id: str, context: dict | None = None) -> ClassificationResult:
    ...         return ClassificationResult(intent=Intent.RAG, confidence=0.9)
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from src.protocols.classification import ClassificationResult, Intent


class ClassificationCacheABC(ABC):
    """
    Abstract base class for classification result caching.

    This ABC matches ClassificationCache protocol exactly, enabling formal
    inheritance while maintaining protocol compatibility.

    Implementations can use LRU cache, Redis, or other caching mechanisms.

    Example:
        >>> class LRUCache(ClassificationCacheABC):
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
    async def get(self, key: str) -> "ClassificationResult | None":
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
        value: "ClassificationResult",
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


class ClassificationStrategyABC(ABC):
    """
    Abstract base class for classification strategies.

    This ABC matches ClassificationStrategy protocol exactly, enabling formal
    inheritance while maintaining protocol compatibility.

    Implementations should be async and thread-safe.

    Example:
        >>> class KeywordClassifier(ClassificationStrategyABC):
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
    ) -> "ClassificationResult":
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
