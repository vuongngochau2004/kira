"""
Interfaces package.

This package contains interface definitions using Abstract Base Classes (ABC)
for stricter interface enforcement and compile-time type checking.

All interfaces use "Base" suffix following Python community conventions.
"""

from src.interfaces.classification import (
    ClassificationCacheBase,
    ClassificationStrategyBase,
    Intent,
    ClassificationResult
)
from src.interfaces.container import (
    DependencyContainerBase,
    ServiceRegistryBase,
    ScopeManagerBase,
    Lifecycle,
    ServiceDescriptor
)
from src.interfaces.handlers import QueryHandlerBase
from src.interfaces.retrieval import (
    RetrieverBase,
    DenseRetrieverBase,
    BM25RetrieverBase,
    HybridRetrieverBase,
    Document
)

__all__ = [
    # Classification interfaces
    "ClassificationCacheBase",
    "ClassificationStrategyBase",
    "Intent",
    "ClassificationResult",

    # Container interfaces
    "DependencyContainerBase",
    "ServiceRegistryBase",
    "ScopeManagerBase",
    "Lifecycle",
    "ServiceDescriptor",

    # Handler interfaces
    "QueryHandlerBase",

    # Retrieval interfaces
    "RetrieverBase",
    "DenseRetrieverBase",
    "BM25RetrieverBase",
    "HybridRetrieverBase",
    "Document",
]
