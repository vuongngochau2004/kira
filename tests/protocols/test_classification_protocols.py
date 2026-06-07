"""
Tests for classification protocols.

Validates protocol compliance and ClassificationResult behavior.
"""

import pytest
from uuid import uuid4

from src.protocols.classification import (
    ClassificationStrategy,
    ClassificationResult,
    Intent,
    ClassificationCache
)


class MockClassificationStrategy:
    """Mock implementation of ClassificationStrategy protocol."""

    async def classify(
        self,
        query: str,
        user_id: str,
        context: dict | None = None
    ) -> ClassificationResult:
        return ClassificationResult(
            intent=Intent.RAG,
            confidence=0.9,
            reason="Mock classification"
        )

    def can_handle(self, query: str, user_id: str) -> bool:
        return bool(query)


class MockClassificationCache:
    """Mock implementation of ClassificationCache protocol."""

    def __init__(self):
        self._cache: dict[str, ClassificationResult] = {}

    async def get(self, key: str) -> ClassificationResult | None:
        return self._cache.get(key)

    async def set(
        self,
        key: str,
        value: ClassificationResult,
        ttl: int | None = None
    ) -> None:
        self._cache[key] = value

    async def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)

    async def clear(self) -> None:
        self._cache.clear()

    def get_stats(self) -> dict:
        return {
            "size": len(self._cache),
            "hit_rate": 0.0,
        }


@pytest.mark.asyncio
async def test_classification_result_creation():
    """Test ClassificationResult creation and validation."""
    result = ClassificationResult(
        intent=Intent.RAG,
        confidence=0.9,
        reason="Test classification",
        metadata={"strategy": "test"}
    )

    assert result.intent == Intent.RAG
    assert result.confidence == 0.9
    assert result.reason == "Test classification"
    assert result.metadata["strategy"] == "test"


@pytest.mark.asyncio
async def test_classification_result_validation():
    """Test ClassificationResult validation."""
    with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
        ClassificationResult(intent=Intent.RAG, confidence=1.5)

    with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
        ClassificationResult(intent=Intent.RAG, confidence=-0.1)


@pytest.mark.asyncio
async def test_classification_result_methods():
    """Test ClassificationResult helper methods."""
    # Test high confidence
    result = ClassificationResult(intent=Intent.RAG, confidence=0.9)
    assert result.is_high_confidence()

    # Test low confidence
    result = ClassificationResult(intent=Intent.RAG, confidence=0.5)
    assert not result.is_high_confidence()

    # Test RAG intent
    result = ClassificationResult(intent=Intent.RAG, confidence=0.9)
    assert result.is_rag_intent()
    assert not result.is_conversational_intent()

    # Test CONVERSATIONAL intent
    result = ClassificationResult(intent=Intent.CONVERSATIONAL, confidence=0.9)
    assert result.is_conversational_intent()
    assert not result.is_rag_intent()


@pytest.mark.asyncio
async def test_classification_result_to_dict():
    """Test ClassificationResult serialization."""
    result = ClassificationResult(
        intent=Intent.RAG,
        confidence=0.9,
        reason="Test",
        metadata={"key": "value"},
        handler_hint="RAGHandler"
    )

    data = result.to_dict()

    assert data["intent"] == "rag"
    assert data["confidence"] == 0.9
    assert data["reason"] == "Test"
    assert data["metadata"]["key"] == "value"
    assert data["handler_hint"] == "RAGHandler"


@pytest.mark.asyncio
async def test_intent_enum():
    """Test Intent enum values."""
    assert Intent.RAG.value == "rag"
    assert Intent.CONVERSATIONAL.value == "conversational"
    assert Intent.DRAFTING.value == "drafting"
    assert Intent.SEMANTIC.value == "semantic"
    assert Intent.UNKNOWN.value == "unknown"

    # Test string conversion
    assert str(Intent.RAG) == "rag"


@pytest.mark.asyncio
async def test_classification_strategy_protocol():
    """Test ClassificationStrategy protocol compliance."""
    strategy = MockClassificationStrategy()

    # Test classify method
    result = await strategy.classify("test query", "user123")

    assert result.intent == Intent.RAG
    assert result.confidence == 0.9
    assert result.reason == "Mock classification"

    # Test can_handle method
    assert strategy.can_handle("test query", "user123")
    assert not strategy.can_handle("", "user123")


@pytest.mark.asyncio
async def test_classification_strategy_with_uuid():
    """Test ClassificationStrategy with UUID user_id."""
    strategy = MockClassificationStrategy()
    user_id = uuid4()

    result = await strategy.classify("test query", str(user_id))

    assert result.intent == Intent.RAG
    assert isinstance(result, ClassificationResult)


@pytest.mark.asyncio
async def test_classification_strategy_with_context():
    """Test ClassificationStrategy with context parameter."""
    strategy = MockClassificationStrategy()
    context = {"conversation_history": []}

    result = await strategy.classify("test query", "user123", context=context)

    assert result.intent == Intent.RAG


@pytest.mark.asyncio
async def test_classification_cache_protocol():
    """Test ClassificationCache protocol compliance."""
    cache = MockClassificationCache()

    # Test set and get
    result = ClassificationResult(intent=Intent.RAG, confidence=0.9)
    await cache.set("test_key", result, ttl=3600)

    cached = await cache.get("test_key")
    assert cached is not None
    assert cached.intent == Intent.RAG

    # Test get non-existent key
    assert await cache.get("non_existent") is None

    # Test invalidate
    await cache.invalidate("test_key")
    assert await cache.get("test_key") is None

    # Test clear
    await cache.set("key1", result)
    await cache.set("key2", result)
    assert await cache.get("key1") is not None

    await cache.clear()
    assert await cache.get("key1") is None
    assert await cache.get("key2") is None

    # Test stats
    stats = cache.get_stats()
    assert "size" in stats
    assert "hit_rate" in stats


@pytest.mark.asyncio
async def test_classification_result_frozen():
    """Test that ClassificationResult is immutable."""
    result = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    with pytest.raises(Exception):  # FrozenInstanceError from dataclasses
        result.confidence = 0.95


@pytest.mark.asyncio
async def test_classification_result_with_handler_hint():
    """Test ClassificationResult with handler_hint."""
    result = ClassificationResult(
        intent=Intent.RAG,
        confidence=0.9,
        handler_hint="RAGHandler"
    )

    assert result.handler_hint == "RAGHandler"

    data = result.to_dict()
    assert data["handler_hint"] == "RAGHandler"
