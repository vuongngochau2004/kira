"""
ABC (Abstract Base Classes) package.

This package contains ABC versions of protocols for stricter interface enforcement.
ABCs use @abstractmethod while Protocols use ... for method stubs.

Key difference:
- Protocol: Structural subtyping (duck typing), more flexible
- ABC: Nominal subtyping, stricter enforcement with @abstractmethod

Migration path: Protocol → ABC for production code enforcement
"""

from src.abc.container import (
    DependencyContainerABC,
    ServiceRegistryABC,
    ScopeManagerABC,
    Lifecycle
)
from src.abc.handlers import QueryHandlerABC
from src.abc.retrieval import (
    RetrieverABC,
    DenseRetrieverABC,
    BM25RetrieverABC,
    HybridRetrieverABC,
    Document
)

__all__ = [
    "DependencyContainerABC",
    "ServiceRegistryABC",
    "ScopeManagerABC",
    "QueryHandlerABC",
    "Lifecycle",
    "RetrieverABC",
    "DenseRetrieverABC",
    "BM25RetrieverABC",
    "HybridRetrieverABC",
    "Document"
]
