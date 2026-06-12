"""
Classification use case for query intent detection.

Orchestrates classification strategies with fallback chain.
"""

import logging
from typing import Any
from uuid import UUID

from src.shared.ports.classification import ClassificationResult, Intent
from src.modules.classification.domain.strategies.composite import CompositeClassifier
from src.modules.classification.domain.strategies.keyword import KeywordStrategy
from src.modules.classification.domain.strategies.llm import LLMStrategy
from src.modules.classification.domain.strategies.cached import CachedStrategy


logger = logging.getLogger(__name__)


class Classification:
    """
    Classification use case for query intent detection.

    Orchestrates classification strategies with fallback chain:
    1. KeywordStrategy - Fast fuzzy file matching (<5ms)
    2. CachedStrategy - LRU cache wrapper (<10ms)
    3. LLMStrategy - LLM-based classification (~800ms)

    Attributes:
        classifier: Composite classifier with strategy chain
        cache: LRU cache for classification results

    Example:
        >>> use_case = Classification()
        >>> result = await use_case.classify("hỏi về contract.pdf", "user123")
        >>> assert result.intent == Intent.RAG
    """

    def __init__(
        self,
        classifier: CompositeClassifier | None = None,
        cache_size: int = 1000,
        cache_ttl: int = 3600
    ):
        """
        Initialize classification use case.

        Args:
            classifier: Custom composite classifier (optional)
            cache_size: Maximum cache size for LRU cache
            cache_ttl: Cache TTL in seconds
        """
        if classifier is None:
            # Build default classification chain
            keyword_strategy = KeywordStrategy()
            llm_strategy = LLMStrategy(temperature=0.1)
            cached_llm = CachedStrategy(
                underlying=llm_strategy,
                cache_size=cache_size,
                ttl=cache_ttl
            )

            classifier = CompositeClassifier([
                keyword_strategy,
                cached_llm
            ])

        self.classifier = classifier
        self.cache = cache_size

    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        """
        Classify query intent using strategy chain with fallback.

        Tries each strategy in order. Returns first result with confidence
        above threshold. Falls back to next strategy if threshold not met.

        Args:
            query: User query string
            user_id: User ID
            context: Additional context (conversation history, etc.)

        Returns:
            ClassificationResult with intent and confidence

        Example:
            >>> result = await use_case.classify("hỏi về contract.pdf", "user123")
            >>> if result.is_rag_intent():
            ...     print("RAG query detected")
        """
        if not query or not query.strip():
            return ClassificationResult(
                intent=Intent.CONVERSATIONAL,
                confidence=0.0,
                reason="Empty query",
                metadata={"use_case": "Classification"}
            )

        try:
            result = await self.classifier.classify(query, user_id, context)

            # Add use case metadata
            return ClassificationResult(
                intent=result.intent,
                confidence=result.confidence,
                reason=result.reason,
                metadata={
                    **result.metadata,
                    "use_case": "Classification"
                },
                handler_hint=result.handler_hint
            )

        except Exception as e:
            logger.error(f"Classification error: {e}", exc_info=True)

            # Fallback to RAG on error (safer default)
            return ClassificationResult(
                intent=Intent.RAG,
                confidence=0.3,
                reason=f"Classification error: {str(e)}",
                metadata={
                    "use_case": "Classification",
                    "error": str(e),
                    "fallback": True
                },
                handler_hint="RAGHandler"
            )

    async def classify_batch(
        self,
        queries: list[tuple[str, str | UUID]],
        context: dict[str, Any] | None = None
    ) -> list[ClassificationResult]:
        """
        Classify multiple queries in batch.

        Args:
            queries: List of (query, user_id) tuples
            context: Additional context (shared across all queries)

        Returns:
            List of ClassificationResult in same order as queries

        Example:
            >>> queries = [("query1", "user1"), ("query2", "user2")]
            >>> results = await use_case.classify_batch(queries)
        """
        results = []

        for query, user_id in queries:
            result = await self.classify(query, user_id, context)
            results.append(result)

        return results

    def get_strategy_info(self) -> dict[str, Any]:
        """
        Get information about classification strategies.

        Returns:
            Dict with strategy names, count, thresholds

        Example:
            >>> info = use_case.get_strategy_info()
            >>> print(f"Strategies: {info['strategy_names']}")
        """
        return {
            "strategy_count": self.classifier.get_strategy_count(),
            "strategy_names": self.classifier.get_strategy_names(),
            "cache_size": self.cache
        }
