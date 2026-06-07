"""
LRU cache implementation for classification results.

Thread-safe async LRU cache with TTL support.
"""

import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, TypeVar, Generic
from uuid import UUID

from src.protocols.classification import ClassificationResult
from src.abc.classification import ClassificationCacheABC


T = TypeVar("T")


@dataclass
class CacheEntry:
    """Cache entry with value and expiration time."""

    value: Any
    expires_at: float | None = None

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return self.expires_at is not None and time.time() > self.expires_at


class AsyncLRUCache(ClassificationCacheABC):
    """
    Async-safe LRU cache with TTL support.

    Attributes:
        maxsize: Maximum number of entries
        ttl: Time-to-live in seconds (None for no expiration)
        _cache: OrderedDict maintaining insertion order

    Example:
        >>> cache = AsyncLRUCache(maxsize=1000, ttl=3600)
        >>> await cache.set("key", ClassificationResult(...))
        >>> result = await cache.get("key")
    """

    def __init__(self, maxsize: int = 1000, ttl: int | None = None):
        """
        Initialize LRU cache.

        Args:
            maxsize: Maximum number of entries (0 for unlimited)
            ttl: Time-to-live in seconds (None for no expiration)
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> ClassificationResult | None:
        """
        Get cached classification result.

        Args:
            key: Cache key

        Returns:
            ClassificationResult if cached and not expired, None otherwise
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1

            return entry.value

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
            ttl: Time-to-live in seconds (None to use default TTL)
        """
        async with self._lock:
            # Calculate expiration time
            expires_at = None
            if ttl is not None:
                expires_at = time.time() + ttl
            elif self.ttl is not None:
                expires_at = time.time() + self.ttl

            # Add or update entry
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            self._cache.move_to_end(key)

            # Enforce maxsize
            if self.maxsize > 0:
                while len(self._cache) > self.maxsize:
                    # Remove oldest (first) entry
                    self._cache.popitem(last=False)

    async def invalidate(self, key: str) -> None:
        """
        Invalidate cache entry.

        Args:
            key: Cache key to invalidate
        """
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with stats: size, hit_rate, ttl, etc.
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "maxsize": self.maxsize,
            "ttl": self.ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }

    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)


def generate_cache_key(query: str, user_id: str | UUID) -> str:
    """
    Generate cache key from query and user_id.

    Args:
        query: User query string
        user_id: User ID

    Returns:
        Cache key string

    Example:
        >>> key = generate_cache_key("test query", "user123")
        >>> assert key == "user123:test query"
    """
    return f"{user_id}:{query}"
