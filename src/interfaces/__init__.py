"""
Interfaces package - Backward compatibility shim.

DEPRECATED: This package is deprecated. Use src.shared.kernel.interfaces instead.
All interfaces have been moved to src.shared.kernel.interfaces as part of
the modular monolith migration (Phase 1).

This module re-exports all interfaces from the new location for backward compatibility.
New code should import directly from src.shared.kernel.interfaces.
"""

# Re-export all interfaces from new location for backward compatibility
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