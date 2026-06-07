"""
Composite classifier with strategy chain and fallback.

Chains multiple classification strategies with fallback logic.
"""

import logging
from typing import Any
from uuid import UUID

from src.abc.classification import ClassificationStrategyABC
from src.protocols.classification import (
    ClassificationResult,
    Intent
)


logger = logging.getLogger(__name__)


class CompositeClassifier(ClassificationStrategyABC):
    """
    Composite classifier with strategy chain and fallback.

    Chains multiple classification strategies in priority order.
    Each strategy is tried in sequence until one returns high confidence.

    Attributes:
        strategies: List of classification strategies in priority order
        thresholds: Confidence threshold for each strategy
        default_intent: Default intent if all strategies fail

    Example:
        >>> from src.classification.strategies.keyword import KeywordStrategy
        >>> from src.classification.strategies.llm import LLMStrategy
        >>> from src.classification.strategies.cached import CachedStrategy
        >>>
        >>> classifier = CompositeClassifier([
        ...     KeywordStrategy(),
        ...     CachedStrategy(LLMStrategy())
        ... ])
        >>> result = await classifier.classify("hỏi về contract.pdf", "user123")
    """

    def __init__(
        self,
        strategies: list[ClassificationStrategyABC],
        thresholds: dict[str, float] | None = None,
        default_intent: Intent = Intent.RAG
    ):
        """
        Initialize composite classifier.

        Args:
            strategies: List of strategies in priority order (fastest first)
            thresholds: Confidence threshold per strategy name
                       (default: {"keyword": 0.7, "cached": 0.6, "llm": 0.5})
            default_intent: Default intent if all strategies fail
        """
        self.strategies = strategies
        self.default_intent = default_intent

        # Default thresholds per strategy type
        self.thresholds = thresholds or {
            "keyword": 0.7,
            "cached": 0.6,
            "llm": 0.5,
            "composite": 0.5,
        }

    def can_handle(self, query: str, user_id: str | UUID) -> bool:
        """
        Check if any strategy can handle the query.

        Args:
            query: User query string
            user_id: User ID

        Returns:
            True if any strategy can handle
        """
        return any(
            strategy.can_handle(query, user_id)
            for strategy in self.strategies
        )

    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        """
        Classify query using strategy chain with fallback.

        Tries each strategy in order. Returns first result with confidence
        above threshold. Falls back to next strategy if threshold not met.

        Args:
            query: User query string
            user_id: User ID
            context: Additional context

        Returns:
            ClassificationResult with intent and confidence

        Example:
            >>> result = await classifier.classify("query", "user123")
            >>> if result.is_high_confidence():
            ...     print(f"Intent: {result.intent}")
        """
        if not query or not query.strip():
            return self._create_default_result("Empty query")

        last_result = None

        # Try each strategy in order
        for i, strategy in enumerate(self.strategies):
            try:
                # Check if strategy can handle
                if not strategy.can_handle(query, user_id):
                    logger.debug(
                        f"Strategy {i+1}/{len(self.strategies)} "
                        f"({strategy.__class__.__name__}) cannot handle query"
                    )
                    continue

                # Classify with strategy
                result = await strategy.classify(query, user_id, context)
                last_result = result

                # Get threshold for this strategy
                strategy_name = strategy.__class__.__name__.lower()
                threshold = self._get_threshold(strategy_name)

                # Check if confidence meets threshold
                if result.confidence >= threshold:
                    logger.info(
                        f"Query classified by {strategy.__class__.__name__}: "
                        f"intent={result.intent.value}, confidence={result.confidence:.2f}"
                    )

                    # Update metadata with strategy info
                    return ClassificationResult(
                        intent=result.intent,
                        confidence=result.confidence,
                        reason=result.reason,
                        metadata={
                            **result.metadata,
                            "strategy_used": strategy.__class__.__name__,
                            "strategy_index": i,
                            "total_strategies": len(self.strategies),
                            "composite": True,
                        },
                        handler_hint=result.handler_hint
                    )

                logger.debug(
                    f"Strategy {strategy.__class__.__name__} confidence "
                    f"({result.confidence:.2f}) below threshold ({threshold:.2f})"
                )

            except Exception as e:
                logger.error(
                    f"Error in strategy {strategy.__class__.__name__}: {e}",
                    exc_info=True
                )
                # Continue to next strategy on error
                continue

        # All strategies failed or below threshold
        if last_result:
            logger.warning(
                f"All strategies below threshold, using last result: "
                f"intent={last_result.intent.value}, confidence={last_result.confidence:.2f}"
            )

            return ClassificationResult(
                intent=last_result.intent,
                confidence=last_result.confidence,
                reason=last_result.reason or "All strategies below threshold",
                metadata={
                    **last_result.metadata,
                    "fallback": True,
                    "composite": True,
                }
            )

        # No result from any strategy - use default
        logger.warning(f"No strategy could classify query, using default: {self.default_intent.value}")

        return self._create_default_result("All strategies failed")

    def _get_threshold(self, strategy_name: str) -> float:
        """
        Get confidence threshold for strategy.

        Args:
            strategy_name: Name of strategy class

        Returns:
            Confidence threshold (0.0 to 1.0)

        Example:
            >>> classifier = CompositeClassifier([])
            >>> classifier._get_threshold("keyword")
            0.7
        """
        # Try exact match first
        if strategy_name in self.thresholds:
            return self.thresholds[strategy_name]

        # Try partial match
        for key, threshold in self.thresholds.items():
            if key in strategy_name:
                return threshold

        # Default threshold
        return 0.5

    def _create_default_result(self, reason: str) -> ClassificationResult:
        """
        Create default classification result.

        Args:
            reason: Reason for default classification

        Returns:
            ClassificationResult with default intent
        """
        return ClassificationResult(
            intent=self.default_intent,
            confidence=0.3,
            reason=reason,
            metadata={"fallback": True, "composite": True}
        )

    def add_strategy(
        self,
        strategy: ClassificationStrategyABC,
        position: int | None = None,
        threshold: float | None = None
    ) -> None:
        """
        Add a strategy to the chain.

        Args:
            strategy: Strategy to add
            position: Position to insert (None for append)
            threshold: Confidence threshold for this strategy

        Example:
            >>> classifier.add_strategy(KeywordStrategy(), position=0, threshold=0.8)
        """
        if position is not None:
            self.strategies.insert(position, strategy)
        else:
            self.strategies.append(strategy)

        if threshold is not None:
            strategy_name = strategy.__class__.__name__.lower()
            self.thresholds[strategy_name] = threshold

    def remove_strategy(self, strategy_class: type) -> bool:
        """
        Remove a strategy from the chain.

        Args:
            strategy_class: Strategy class to remove

        Returns:
            True if strategy was removed, False if not found

        Example:
            >>> from src.classification.strategies.keyword import KeywordStrategy
            >>> classifier.remove_strategy(KeywordStrategy)
            True
        """
        original_length = len(self.strategies)

        self.strategies = [
            s for s in self.strategies
            if not isinstance(s, strategy_class)
        ]

        return len(self.strategies) < original_length

    def get_strategy_count(self) -> int:
        """
        Get number of strategies in chain.

        Returns:
            Number of strategies

        Example:
            >>> count = classifier.get_strategy_count()
            >>> print(f"Strategies: {count}")
        """
        return len(self.strategies)

    def get_strategy_names(self) -> list[str]:
        """
        Get names of strategies in chain.

        Returns:
            List of strategy class names

        Example:
            >>> names = classifier.get_strategy_names()
            >>> print(f"Strategies: {', '.join(names)}")
        """
        return [s.__class__.__name__ for s in self.strategies]
