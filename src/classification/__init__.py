"""
Classification package for K.I.R.A query intent detection.

This package implements the Strategy pattern for query classification,
following DRY principle and SOLID design.

Classification Chain (fastest to slowest):
1. KeywordStrategy - Fuzzy file matching, keyword detection (<5ms)
2. CachedStrategy - LRU cache of recent classifications (<10ms)
3. LLMStrategy - Fallback to LLM classifier (~800ms)

Usage:
    >>> from classification.strategies.composite import CompositeClassifier
    >>> classifier = CompositeClassifier([
    ...     KeywordStrategy(),
    ...     CachedStrategy(LLMStrategy())
    ... ])
    >>> result = await classifier.classify("hỏi về contract.pdf", "user123")
"""

from classification.strategies.composite import CompositeClassifier
from classification.strategies.keyword import KeywordStrategy
from classification.strategies.llm import LLMStrategy
from classification.strategies.cached import CachedStrategy

__all__ = [
    "CompositeClassifier",
    "KeywordStrategy",
    "LLMStrategy",
    "CachedStrategy",
]
