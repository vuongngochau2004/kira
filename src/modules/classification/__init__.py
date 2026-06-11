"""
Classification module for K.I.R.A query intent detection.

This module implements the Strategy pattern for query classification,
following DRY principle and SOLID design.

Classification Chain (fastest to slowest):
1. KeywordStrategy - Fuzzy file matching, keyword detection (<5ms)
2. CachedStrategy - LRU cache of recent classifications (<10ms)
3. LLMStrategy - Fallback to LLM classifier (~800ms)

Usage:
    >>> from src.modules.classification.application import ClassificationUseCase
    >>> use_case = ClassificationUseCase()
    >>> result = await use_case.classify("hỏi về contract.pdf", "user123")
    >>> assert result.intent == Intent.RAG

Module Structure:
- application/ - Use cases and DTOs
- domain/ - Business logic (strategies, cache)
- infrastructure/ - External adapters (empty for now)
- api/ - Request/response DTOs
"""

from src.modules.classification.application import ClassificationUseCase, ClassifyQuery, ClassificationResultDTO
from src.modules.classification.domain import (
    CompositeClassifier,
    KeywordStrategy,
    LLMStrategy,
    CachedStrategy,
    AsyncLRUCache,
    generate_cache_key
)
from src.modules.classification.api import (
    ClassifyRequest,
    BatchClassifyRequest,
    ClassificationResponse,
    BatchClassificationResponse,
    StrategyInfoResponse
)

__all__ = [
    # Application layer
    "ClassificationUseCase",
    "ClassifyQuery",
    "ClassificationResultDTO",
    # Domain layer
    "CompositeClassifier",
    "KeywordStrategy",
    "LLMStrategy",
    "CachedStrategy",
    "AsyncLRUCache",
    "generate_cache_key",
    # API layer
    "ClassifyRequest",
    "BatchClassifyRequest",
    "ClassificationResponse",
    "BatchClassificationResponse",
    "StrategyInfoResponse",
]
