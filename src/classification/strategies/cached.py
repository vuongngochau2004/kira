"""
Cached classification strategy wrapper.

Wraps any classification strategy with LRU cache for performance.
"""

from typing import Any
from uuid import UUID

from src.interfaces.classification import ClassificationStrategyBase, ClassificationResult
from src.classification.cache.lru_cache import AsyncLRUCache, generate_cache_key


class CachedStrategy(ClassificationStrategyBase):
    """
    Cached wrapper for classification strategies.

    Wraps any ClassificationStrategy with LRU cache to improve performance.
    Target latency: <10ms (p95) for cache hits.

    Attributes:
        underlying: Underlying classification strategy
        cache: LRU cache for classification results
        cache_ttl: Cache TTL in seconds

    Example:
        >>> underlying = LLMStrategy(llm_client=...)
        >>> strategy = CachedStrategy(underlying, cache_size=1000, ttl=3600)
        >>> result = await strategy.classify("query", "user123")
    """

    def __init__(
        self,
        underlying: ClassificationStrategyBase,
        cache_size: int = 1000,
        ttl: int = 3600
    ):
        """
        Initialize cached strategy.

        Args:
            underlying: Underlying classification strategy to wrap
            cache_size: Maximum cache size (0 for unlimited)
            ttl: Cache TTL in seconds (None for no expiration)
        """
        self.underlying = underlying
        self.cache = AsyncLRUCache(maxsize=cache_size, ttl=ttl)
        self.cache_ttl = ttl

    def can_handle(self, query: str, user_id: str | UUID) -> bool:
        """
        Quick check if underlying strategy can handle the query.

        Args:
            query: User query string
            user_id: User ID

        Returns:
            True if underlying strategy can handle
        """
        return self.underlying.can_handle(query, user_id)

    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        """
        Classify query with caching.

        Args:
            query: User query string
            user_id: User ID
            context: Additional context

        Returns:
            ClassificationResult (cached or fresh)
        """
        # Generate cache key
        cache_key = generate_cache_key(query, str(user_id))

        # Try cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            # Update metadata to indicate cache hit
            return ClassificationResult(
                intent=cached_result.intent,
                confidence=cached_result.confidence,
                reason=cached_result.reason,
                metadata={
                    **cached_result.metadata,
                    "cached": True,
                    "strategy": "cached_wrapper"
                }
            )

        # Cache miss - delegate to underlying strategy
        result = await self.underlying.classify(query, user_id, context)

        # Cache the result
        await self.cache.set(cache_key, result, ttl=self.cache_ttl)

        # Update metadata to indicate cache miss
        return ClassificationResult(
            intent=result.intent,
            confidence=result.confidence,
            reason=result.reason,
            metadata={
                **result.metadata,
                "cached": False,
                "strategy": "cached_wrapper"
            }
        )

    async def invalidate(self, query: str, user_id: str | UUID) -> None:
        """
        Invalidate cache entry for specific query.

        Args:
            query: User query string
            user_id: User ID

        Example:
            >>> await strategy.invalidate("old query", "user123")
        """
        cache_key = generate_cache_key(query, str(user_id))
        await self.cache.invalidate(cache_key)

    async def clear_cache(self) -> None:
        """
        Clear entire cache.

        Example:
            >>> await strategy.clear_cache()
        """
        await self.cache.clear()

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats: hit_rate, size, etc.

        Example:
            >>> stats = strategy.get_cache_stats()
            >>> print(f"Cache hit rate: {stats['hit_rate']:.2%}")
        """
        return self.cache.get_stats()

    async def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed

        Example:
            >>> removed = await strategy.cleanup_expired()
            >>> print(f"Removed {removed} expired entries")
        """
        return await self.cache.cleanup_expired()
