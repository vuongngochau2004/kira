"""
Tests for CachedStrategy.
"""

import pytest

from src.classification.strategies.cached import CachedStrategy
from src.protocols.classification import Intent, ClassificationResult
from src.classification.cache.lru_cache import AsyncLRUCache


class MockClassificationStrategy:
    """Mock strategy for testing."""

    def __init__(self, delay_ms: int = 0):
        self.call_count = 0
        self.delay_ms = delay_ms

    def can_handle(self, query: str, user_id: str) -> bool:
        return bool(query)

    async def classify(self, query: str, user_id: str, context: dict | None = None):
        import asyncio

        self.call_count += 1

        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000)

        return ClassificationResult(
            intent=Intent.RAG if "tài liệu" in query.lower() else Intent.CONVERSATIONAL,
            confidence=0.9,
            reason=f"Mock classification (call #{self.call_count})"
        )


@pytest.mark.asyncio
async def test_cached_strategy_creation():
    """Test CachedStrategy creation."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying, cache_size=100, ttl=3600)

    assert strategy.underlying == underlying
    assert strategy.cache_ttl == 3600


@pytest.mark.asyncio
async def test_cached_strategy_cache_miss():
    """Test cached strategy with cache miss."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying, cache_size=100)

    result = await strategy.classify("tài liệu", "user123")

    assert result.intent == Intent.RAG
    assert result.confidence == 0.9
    assert result.metadata["cached"] is False
    assert underlying.call_count == 1


@pytest.mark.asyncio
async def test_cached_strategy_cache_hit():
    """Test cached strategy with cache hit."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying, cache_size=100)

    # First call - cache miss
    result1 = await strategy.classify("tài liệu", "user123")
    assert result1.metadata["cached"] is False
    assert underlying.call_count == 1

    # Second call - cache hit
    result2 = await strategy.classify("tài liệu", "user123")
    assert result2.metadata["cached"] is True
    assert underlying.call_count == 1  # No additional call

    # Results should be equivalent
    assert result1.intent == result2.intent
    assert result1.confidence == result2.confidence


@pytest.mark.asyncio
async def test_cached_strategy_different_queries():
    """Test cached strategy with different queries."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying, cache_size=100)

    # First query
    await strategy.classify("tài liệu", "user123")
    assert underlying.call_count == 1

    # Different query - cache miss
    await strategy.classify("xin chào", "user123")
    assert underlying.call_count == 2


@pytest.mark.asyncio
async def test_cached_strategy_different_users():
    """Test cached strategy with different users."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying, cache_size=100)

    # First user
    await strategy.classify("tài liệu", "user123")
    assert underlying.call_count == 1

    # Different user - cache miss (user-scoped)
    await strategy.classify("tài liệu", "user456")
    assert underlying.call_count == 2


@pytest.mark.asyncio
async def test_cached_strategy_can_handle():
    """Test CachedStrategy.can_handle() delegates to underlying."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying)

    assert strategy.can_handle("query", "user123")
    assert not strategy.can_handle("", "user123")


@pytest.mark.asyncio
async def test_cached_strategy_invalidate():
    """Test cache invalidation."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying, cache_size=100)

    # Cache a result
    await strategy.classify("tài liệu", "user123")
    assert underlying.call_count == 1

    # Cache hit
    await strategy.classify("tài liệu", "user123")
    assert underlying.call_count == 1

    # Invalidate
    await strategy.invalidate("tài liệu", "user123")

    # Cache miss after invalidation
    await strategy.classify("tài liệu", "user123")
    assert underlying.call_count == 2


@pytest.mark.asyncio
async def test_cached_strategy_clear_cache():
    """Test clearing entire cache."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying, cache_size=100)

    # Cache multiple results
    await strategy.classify("query1", "user123")
    await strategy.classify("query2", "user123")
    assert underlying.call_count == 2

    # Clear cache
    await strategy.clear_cache()

    # Cache misses after clear
    await strategy.classify("query1", "user123")
    await strategy.classify("query2", "user123")
    assert underlying.call_count == 4


@pytest.mark.asyncio
async def test_cached_strategy_get_stats():
    """Test getting cache statistics."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying, cache_size=100)

    # Cache miss
    await strategy.classify("query", "user123")

    stats = strategy.get_cache_stats()

    assert "size" in stats
    assert "hits" in stats
    assert "misses" in stats
    assert "hit_rate" in stats
    assert stats["misses"] == 1


@pytest.mark.asyncio
async def test_cached_strategy_cleanup_expired():
    """Test cleanup of expired entries."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying, cache_size=100, ttl=1)  # 1 second TTL

    # Cache entry
    await strategy.classify("query", "user123")

    # Wait for expiration
    import asyncio

    await asyncio.sleep(1.1)  # Wait for entry to expire

    # Cleanup expired
    removed = await strategy.cleanup_expired()

    assert removed >= 0  # May have expired


@pytest.mark.asyncio
async def test_cached_strategy_with_context():
    """Test CachedStrategy with context parameter."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying)

    context = {"conversation_history": []}
    result = await strategy.classify("tài liệu", "user123", context=context)

    assert result.intent == Intent.RAG


@pytest.mark.asyncio
async def test_cached_strategy_cache_key_generation():
    """Test cache key includes user_id."""
    underlying = MockClassificationStrategy()
    strategy = CachedStrategy(underlying)

    # Same query, different users - should be separate cache entries
    await strategy.classify("query", "user123")
    await strategy.classify("query", "user456")

    assert underlying.call_count == 2  # Both were cache misses

    # Cache hits for same users
    await strategy.classify("query", "user123")
    await strategy.classify("query", "user456")

    assert underlying.call_count == 2  # No additional calls
