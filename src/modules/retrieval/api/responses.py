"""Response DTOs for retrieval module API.

Defines Pydantic models for search response formatting.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime


class SearchResult(BaseModel):
    """Single search result with metadata."""

    text: str = Field(..., description="Chunk text content")
    content: str = Field(..., description="Alias for text field")
    document_id: Optional[str] = Field(None, description="Source document ID")
    chunk_index: Optional[int] = Field(None, description="Chunk index in document")
    page_number: Optional[int] = Field(None, description="Page number if applicable")
    score: float = Field(..., description="Relevance score from retrieval")
    rrf_score: Optional[float] = Field(None, description="RRF fusion score")
    rerank_score: Optional[float] = Field(None, description="LLM reranking score")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Nội dung văn bản hợp đồng lao động...",
                    "content": "Nội dung văn bản hợp đồng lao động...",
                    "document_id": "uuid-here",
                    "chunk_index": 0,
                    "page_number": 1,
                    "score": 0.85,
                    "rrf_score": 0.12,
                    "rerank_score": 0.90,
                    "metadata": {"user_id": "user123", "filename": "contract.pdf"},
                }
            ]
        }
    }


class SearchResponse(BaseModel):
    """Standard response for search operations."""

    results: list[SearchResult] = Field(..., description="List of search results")
    total: int = Field(..., description="Total number of results returned")
    query: str = Field(..., description="Original query text")
    retrieval_method: str = Field(
        ...,
        description="Method used: hybrid, dense_only, bm25_only"
    )
    latency_ms: Optional[int] = Field(None, description="Search latency in milliseconds")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "results": [],
                    "total": 5,
                    "query": "tìm kiếm hợp đồng lao động",
                    "retrieval_method": "hybrid",
                    "latency_ms": 150,
                    "timestamp": "2026-06-11T14:00:00Z",
                }
            ]
        }
    }


class RerankResponse(BaseModel):
    """Response for document reranking operations."""

    results: list[SearchResult] = Field(..., description="Reranked documents")
    original_count: int = Field(..., description="Original number of documents")
    reranked_count: int = Field(..., description="Number after reranking")
    method: str = Field(..., description="Reranking method used")
    latency_ms: Optional[int] = Field(None, description="Reranking latency in ms")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "results": [],
                    "original_count": 10,
                    "reranked_count": 5,
                    "method": "llm_rerank",
                    "latency_ms": 800,
                    "timestamp": "2026-06-11T14:00:00Z",
                }
            ]
        }
    }


class HealthCheckResponse(BaseModel):
    """Response for retrieval module health check."""

    status: str = Field(..., description="Health status: healthy, degraded, unhealthy")
    services: dict[str, str] = Field(
        ...,
        description="Status of individual services (qdrant, bm25)"
    )
    version: str = Field(..., description="Module version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Check timestamp"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "services": {
                        "qdrant": "connected",
                        "bm25": "active",
                    },
                    "version": "1.0.0",
                    "timestamp": "2026-06-11T14:00:00Z",
                }
            ]
        }
    }


__all__ = [
    "SearchResult",
    "SearchResponse",
    "RerankResponse",
    "HealthCheckResponse",
]
