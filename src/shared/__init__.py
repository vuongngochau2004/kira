"""K.I.R.A Shared Kernel and Infrastructure.

Core abstractions, base classes, domain entities, and infrastructure
that are shared across all modules in the modular monolith architecture.
"""

# Shared Kernel - ABC interfaces, DI, base classes
from src.shared.domain.entities.conversation import ConversationEntity

# Shared Domain - Domain entities and value objects
from src.shared.domain.entities.document import DocumentEntity
from src.shared.domain.entities.user import UserEntity
from src.shared.kernel.di import FeatureFlagManager, ServiceContainer, ServiceRegistry
from src.shared.ports import (
    BM25RetrieverBase,
    Citation,
    ClassificationCacheBase,
    ClassificationResult,
    ClassificationStrategyBase,
    DenseRetrieverBase,
    DependencyContainerBase,
    Document,
    HandlerConfig,
    HandlerResult,
    HybridRetrieverBase,
    Intent,
    Lifecycle,
    QueryHandlerBase,
    RetrieverBase,
    ScopeManagerBase,
    ServiceDescriptor,
    ServiceRegistryBase,
)

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
    # Domain Entities
    "DocumentEntity",
    "ConversationEntity",
    "UserEntity",
]
