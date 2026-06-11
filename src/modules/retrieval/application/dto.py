"""Data transfer objects for retrieval module.

Defines request/response DTOs for search operations.
"""

from pydantic import BaseModel, Field
from typing import Any
from uuid import UUID


class SearchRequest(BaseModel):
    """Request for hybrid search."""

    query_embedding: list[float] = Field(..., description="Query vector for dense search")
    query_text: str = Field(..., min_length=1, description="Query text for BM25 search")
    user_id: str | None = Field(None, description="Optional user ID filter")
    k: int = Field(5, ge=1, le=50, description="Number of results")
    rrf_k: int = Field(60, ge=1, description="RRF constant")
    enable_rerank: bool = Field(False, description="Enable LLM reranking")

    model_config = {"json_schema_extra": {"examples": [
        {
            "query_embedding": [0.1, 0.2, 0.3],
            "query_text": "tìm kiếm văn bản",
            "user_id": "user123",
            "k": 5,
            "rrf_k": 60,
            "enable_rerank": True,
        }
    ]}}


class SearchResult(BaseModel):
    """Single search result with metadata."""

    text: str = Field(..., description="Chunk text content")
    content: str = Field(..., description="Alias for text")
    document_id: str | None = Field(None, description="Source document ID")
    chunk_index: int | None = Field(None, description="Chunk index in document")
    page_number: int | None = Field(None, description="Page number if applicable")
    score: float = Field(..., description="Relevance score")
    rrf_score: float | None = Field(None, description="RRF fusion score")
    rerank_score: float | None = Field(None, description="LLM reranking score")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"json_schema_extra": {"examples": [
        {
            "text": "Sample document text",
            "content": "Sample document text",
            "document_id": "uuid",
            "chunk_index": 0,
            "page_number": 1,
            "score": 0.85,
            "rrf_score": 0.12,
            "rerank_score": 0.90,
            "metadata": {"user_id": "user123"},
        }
    ]}}


class SearchResponse(BaseModel):
    """Response for hybrid search."""

    results: list[SearchResult] = Field(..., description="List of search results")
    total: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Original query text")
    retrieval_method: str = Field(..., description="Method used: hybrid, dense_only, bm25_only")
    latency_ms: int | None = Field(None, description="Search latency in milliseconds")

    model_config = {"json_schema_extra": {"examples": [
        {
            "results": [],
            "total": 5,
            "query": "tìm kiếm văn bản",
            "retrieval_method": "hybrid",
            "latency_ms": 150,
        }
    ]}}


__all__ = ["SearchRequest", "SearchResult", "SearchResponse"]
