"""API layer for retrieval module.

Exports request/response DTOs for search operations.
"""

from src.modules.retrieval.api.requests import (
    HybridSearchRequest,
    DenseSearchRequest,
    BM25SearchRequest,
    RerankRequest,
)
from src.modules.retrieval.api.responses import (
    SearchResult,
    SearchResponse,
    RerankResponse,
    HealthCheckResponse,
)

__all__ = [
    "HybridSearchRequest",
    "DenseSearchRequest",
    "BM25SearchRequest",
    "RerankRequest",
    "SearchResult",
    "SearchResponse",
    "RerankResponse",
    "HealthCheckResponse",
]
