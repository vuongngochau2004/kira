"""K.I.R.A Shared Kernel.

Core abstractions, base classes, and dependency injection
that are shared across all modules in the modular monolith architecture.
"""

from src.shared.kernel.interfaces import (
    ClassificationStrategyBase,
    ClassificationResult,
    ClassificationCacheBase,
    Intent,
    QueryHandlerBase,
    HandlerResult,
    HandlerConfig,
    Citation,
    RetrieverBase,
    DenseRetrieverBase,
    BM25RetrieverBase,
    HybridRetrieverBase,
    Document,
    Lifecycle,
    DependencyContainerBase,
    ServiceRegistryBase,
    ScopeManagerBase,
    ServiceDescriptor,
)
from src.shared.kernel.di import ServiceContainer, ServiceRegistry, FeatureFlagManager

__all__ = [
    # Classification
    "ClassificationStrategyBase",
    "ClassificationResult",
    "ClassificationCacheBase",
    "Intent",
    # Handlers
    "QueryHandlerBase",
    "HandlerResult",
    "HandlerConfig",
    "Citation",
    # Retrieval
    "RetrieverBase",
    "DenseRetrieverBase",
    "BM25RetrieverBase",
    "HybridRetrieverBase",
    "Document",
    # Container
    "Lifecycle",
    "DependencyContainerBase",
    "ServiceRegistryBase",
    "ScopeManagerBase",
    "ServiceDescriptor",
    # DI
    "ServiceContainer",
    "ServiceRegistry",
    "FeatureFlagManager",
]