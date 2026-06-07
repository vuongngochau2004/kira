"""
Tests for CompositeClassifier.
"""

import pytest

from src.classification.strategies.composite import CompositeClassifier
from src.protocols.classification import Intent, ClassificationResult


class HighConfidenceStrategy:
    """Mock strategy that returns high confidence."""

    def __init__(self, name: str = "HighConfidence"):
        self.name = name
        self.call_count = 0

    def can_handle(self, query: str, user_id: str) -> bool:
        return True

    async def classify(self, query: str, user_id: str, context: dict | None = None):
        self.call_count += 1
        return ClassificationResult(
            intent=Intent.RAG,
            confidence=0.95,
            reason=f"{self.name} classification"
        )


class LowConfidenceStrategy:
    """Mock strategy that returns low confidence."""

    def __init__(self, name: str = "LowConfidence"):
        self.name = name
        self.call_count = 0

    def can_handle(self, query: str, user_id: str) -> bool:
        return True

    async def classify(self, query: str, user_id: str, context: dict | None = None):
        self.call_count += 1
        return ClassificationResult(
            intent=Intent.CONVERSATIONAL,
            confidence=0.5,
            reason=f"{self.name} classification"
        )


class FailingStrategy:
    """Mock strategy that raises exception."""

    def __init__(self, name: str = "Failing"):
        self.name = name
        self.call_count = 0

    def can_handle(self, query: str, user_id: str) -> bool:
        return True

    async def classify(self, query: str, user_id: str, context: dict | None = None):
        self.call_count += 1
        raise Exception(f"{self.name} failed")


class ConditionalStrategy:
    """Mock strategy that only handles certain queries."""

    def __init__(self, can_handle_value: bool, name: str = "Conditional"):
        self.can_handle_value = can_handle_value
        self.name = name
        self.call_count = 0

    def can_handle(self, query: str, user_id: str) -> bool:
        return self.can_handle_value

    async def classify(self, query: str, user_id: str, context: dict | None = None):
        self.call_count += 1
        return ClassificationResult(
            intent=Intent.RAG,
            confidence=0.8,
            reason=f"{self.name} classification"
        )


@pytest.mark.asyncio
async def test_composite_classifier_creation():
    """Test CompositeClassifier creation."""
    strategies = [HighConfidenceStrategy(), LowConfidenceStrategy()]
    classifier = CompositeClassifier(strategies)

    assert len(classifier.strategies) == 2
    assert classifier.default_intent == Intent.RAG


@pytest.mark.asyncio
async def test_composite_classifier_high_confidence_first():
    """Test composite with high confidence first strategy."""
    strategies = [HighConfidenceStrategy(), LowConfidenceStrategy()]
    classifier = CompositeClassifier(strategies)

    result = await classifier.classify("query", "user123")

    assert result.intent == Intent.RAG
    assert result.confidence == 0.95
    assert "HighConfidence" in result.metadata["strategy_used"]
    assert strategies[0].call_count == 1
    assert strategies[1].call_count == 0  # Not called


@pytest.mark.asyncio
async def test_composite_classifier_fallback_to_second():
    """Test composite fallback to second strategy."""
    strategies = [LowConfidenceStrategy(), HighConfidenceStrategy()]
    classifier = CompositeClassifier(strategies, thresholds={"lowconfidence": 0.6})

    result = await classifier.classify("query", "user123")

    assert result.intent == Intent.RAG
    assert result.confidence == 0.95
    assert "HighConfidence" in result.metadata["strategy_used"]
    assert strategies[0].call_count == 1  # Called but below threshold (0.5 < 0.6)
    assert strategies[1].call_count == 1  # Called and succeeded


@pytest.mark.asyncio
async def test_composite_classifier_all_below_threshold():
    """Test composite when all strategies below threshold."""
    strategies = [LowConfidenceStrategy(), LowConfidenceStrategy()]
    classifier = CompositeClassifier(strategies, thresholds={"lowconfidence": 0.6})

    result = await classifier.classify("query", "user123")

    assert result.intent == Intent.CONVERSATIONAL
    assert result.confidence == 0.5
    assert result.metadata.get("fallback") is True  # Fallback to last result


@pytest.mark.asyncio
async def test_composite_classifier_with_failing_strategy():
    """Test composite with failing strategy continues to next."""
    strategies = [FailingStrategy(), HighConfidenceStrategy()]
    classifier = CompositeClassifier(strategies)

    result = await classifier.classify("query", "user123")

    assert result.intent == Intent.RAG
    assert result.confidence == 0.95
    assert strategies[0].call_count == 1  # Called and failed
    assert strategies[1].call_count == 1  # Called and succeeded


@pytest.mark.asyncio
async def test_composite_classifier_can_handle():
    """Test CompositeClassifier.can_handle() checks all strategies."""
    strategies = [
        ConditionalStrategy(can_handle_value=False),
        ConditionalStrategy(can_handle_value=True)
    ]
    classifier = CompositeClassifier(strategies)

    assert classifier.can_handle("query", "user123")


@pytest.mark.asyncio
async def test_composite_classifier_none_can_handle():
    """Test composite when no strategy can handle."""
    strategies = [
        ConditionalStrategy(can_handle_value=False),
        ConditionalStrategy(can_handle_value=False)
    ]
    classifier = CompositeClassifier(strategies)

    assert not classifier.can_handle("query", "user123")


@pytest.mark.asyncio
async def test_composite_classifier_empty_query():
    """Test composite with empty query."""
    strategies = [HighConfidenceStrategy()]
    classifier = CompositeClassifier(strategies)

    result = await classifier.classify("", "user123")

    assert result.confidence < 0.5
    assert "Empty" in result.reason


@pytest.mark.asyncio
async def test_composite_classifier_custom_thresholds():
    """Test composite with custom thresholds."""
    strategies = [LowConfidenceStrategy()]
    classifier = CompositeClassifier(
        strategies,
        thresholds={"lowconfidence": 0.4}  # Below 0.5
    )

    result = await classifier.classify("query", "user123")

    assert result.intent == Intent.CONVERSATIONAL
    assert result.confidence == 0.5
    assert "LowConfidence" in result.metadata.get("strategy_used", "")


@pytest.mark.asyncio
async def test_composite_classifier_add_strategy():
    """Test adding strategy to composite."""
    strategies = [LowConfidenceStrategy()]
    classifier = CompositeClassifier(strategies)

    new_strategy = HighConfidenceStrategy()
    classifier.add_strategy(new_strategy, position=0)

    assert len(classifier.strategies) == 2
    assert classifier.strategies[0] == new_strategy


@pytest.mark.asyncio
async def test_composite_classifier_remove_strategy():
    """Test removing strategy from composite."""
    strategies = [HighConfidenceStrategy(), LowConfidenceStrategy()]
    classifier = CompositeClassifier(strategies)

    result = classifier.remove_strategy(HighConfidenceStrategy)

    assert result is True
    assert len(classifier.strategies) == 1
    assert isinstance(classifier.strategies[0], LowConfidenceStrategy)


@pytest.mark.asyncio
async def test_composite_classifier_remove_nonexistent():
    """Test removing non-existent strategy."""
    strategies = [LowConfidenceStrategy()]
    classifier = CompositeClassifier(strategies)

    result = classifier.remove_strategy(HighConfidenceStrategy)

    assert result is False
    assert len(classifier.strategies) == 1


@pytest.mark.asyncio
async def test_composite_classifier_get_strategy_count():
    """Test getting strategy count."""
    strategies = [HighConfidenceStrategy(), LowConfidenceStrategy()]
    classifier = CompositeClassifier(strategies)

    assert classifier.get_strategy_count() == 2


@pytest.mark.asyncio
async def test_composite_classifier_get_strategy_names():
    """Test getting strategy names."""
    strategies = [HighConfidenceStrategy(), LowConfidenceStrategy()]
    classifier = CompositeClassifier(strategies)

    names = classifier.get_strategy_names()

    assert any("HighConfidence" in name for name in names)
    assert any("LowConfidence" in name for name in names)


@pytest.mark.asyncio
async def test_composite_classifier_with_context():
    """Test composite with context parameter."""
    strategies = [HighConfidenceStrategy()]
    classifier = CompositeClassifier(strategies)

    context = {"conversation_history": []}
    result = await classifier.classify("query", "user123", context=context)

    assert result.intent == Intent.RAG


@pytest.mark.asyncio
async def test_composite_classifier_metadata():
    """Test composite includes metadata about strategy chain."""
    strategies = [HighConfidenceStrategy(), LowConfidenceStrategy()]
    classifier = CompositeClassifier(strategies)

    result = await classifier.classify("query", "user123")

    assert "HighConfidence" in result.metadata["strategy_used"]
    assert result.metadata["strategy_index"] == 0
    assert result.metadata["total_strategies"] == 2
    assert result.metadata["composite"] is True


@pytest.mark.asyncio
async def test_composite_classifier_default_intent():
    """Test composite with custom default intent."""
    strategies = [FailingStrategy()]
    classifier = CompositeClassifier(
        strategies,
        default_intent=Intent.CONVERSATIONAL
    )

    result = await classifier.classify("query", "user123")

    assert result.intent == Intent.CONVERSATIONAL
    assert result.metadata["fallback"] is True
