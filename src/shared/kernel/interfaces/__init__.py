"""
Interfaces package.

This package contains interface definitions using Abstract Base Classes (ABC)
for stricter interface enforcement and compile-time type checking.

All interfaces use "Base" suffix following Python community conventions.
"""

from src.shared.kernel.interfaces.classification import (
    ClassificationCacheBase,
    ClassificationStrategyBase,
    Intent,
    ClassificationResult
)
from src.shared.kernel.interfaces.container import (
    DependencyContainerBase,
    ServiceRegistryBase,
    ScopeManagerBase,
    Lifecycle,
    ServiceDescriptor
)
from src.shared.kernel.interfaces.handlers import QueryHandlerBase, HandlerResult, HandlerConfig, Citation
from src.shared.kernel.interfaces.retrieval import (
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
    "HandlerResult",
    "HandlerConfig",
    "Citation",

    # Retrieval interfaces
    "RetrieverBase",
    "DenseRetrieverBase",
    "BM25RetrieverBase",
    "HybridRetrieverBase",
    "Document",
]
