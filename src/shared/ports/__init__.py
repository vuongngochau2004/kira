"""Shared application ports and contracts.

Ports define the contracts that application and domain code depend on.
Infrastructure adapters provide concrete implementations for external systems.
"""

from src.shared.ports.classification import (
    ClassificationCacheBase,
    ClassificationResult,
    ClassificationStrategyBase,
    Intent,
)
from src.shared.ports.container import (
    DependencyContainerBase,
    Lifecycle,
    ScopeManagerBase,
    ServiceDescriptor,
    ServiceRegistryBase,
)
from src.shared.ports.document_repository import DocumentRepositoryPort
from src.shared.ports.embedding import EmbeddingPort
from src.shared.ports.handlers import Citation, HandlerConfig, HandlerResult, QueryHandlerBase
from src.shared.ports.keyword_index import KeywordIndexPort
from src.shared.ports.llm import LLMPort
from src.shared.ports.ocr import OCRPort
from src.shared.ports.retrieval import (
    BM25RetrieverBase,
    DenseRetrieverBase,
    Document,
    HybridRetrieverBase,
    RetrieverBase,
)
from src.shared.ports.storage import StoragePort
from src.shared.ports.vector_store import SearchResult, VectorDocument, VectorStorePort

__all__ = [
    "BM25RetrieverBase",
    "ClassificationCacheBase",
    "ClassificationResult",
    "ClassificationStrategyBase",
    "Citation",
    "DependencyContainerBase",
    "DenseRetrieverBase",
    "Document",
    "DocumentRepositoryPort",
    "EmbeddingPort",
    "HandlerConfig",
    "HandlerResult",
    "HybridRetrieverBase",
    "Intent",
    "KeywordIndexPort",
    "Lifecycle",
    "LLMPort",
    "OCRPort",
    "QueryHandlerBase",
    "RetrieverBase",
    "ScopeManagerBase",
    "StoragePort",
    "ServiceDescriptor",
    "ServiceRegistryBase",
    "SearchResult",
    "VectorDocument",
    "VectorStorePort",
]
