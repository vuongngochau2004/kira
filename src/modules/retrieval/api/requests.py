"""Request DTOs for retrieval module API.

Defines Pydantic models for search request validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


class HybridSearchRequest(BaseModel):
    """Request for hybrid search combining dense and BM25 retrieval."""

    query_embedding: list[float] = Field(
        ...,
        description="Query vector for dense search",
        min_length=1
    )
    query_text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Query text for BM25 search"
    )
    user_id: Optional[str] = Field(
        None,
        description="Optional user ID filter for multi-tenant isolation"
    )
    k: int = Field(
        5,
        ge=1,
        le=50,
        description="Number of results to return"
    )
    rrf_k: int = Field(
        60,
        ge=1,
        description="RRF constant for fusion (higher = more balanced ranking)"
    )
    enable_rerank: bool = Field(
        False,
        description="Enable LLM-based reranking for improved precision"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query_embedding": [0.1, 0.2, 0.3, 0.4],
                    "query_text": "tìm kiếm hợp đồng lao động",
                    "user_id": "user123",
                    "k": 5,
                    "rrf_k": 60,
                    "enable_rerank": True,
                }
            ]
        }
    }


class DenseSearchRequest(BaseModel):
    """Request for dense-only vector search."""

    query_embedding: list[float] = Field(
        ...,
        description="Query vector for dense search",
        min_length=1
    )
    user_id: Optional[str] = Field(
        None,
        description="Optional user ID filter"
    )
    k: int = Field(
        5,
        ge=1,
        le=50,
        description="Number of results"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query_embedding": [0.1, 0.2, 0.3, 0.4],
                    "user_id": "user123",
                    "k": 10,
                }
            ]
        }
    }


class BM25SearchRequest(BaseModel):
    """Request for BM25 keyword search."""

    query_text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Query text for BM25 search"
    )
    user_id: Optional[str] = Field(
        None,
        description="Optional user ID filter"
    )
    k: int = Field(
        5,
        ge=1,
        le=50,
        description="Number of results"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query_text": "hợp đồng lao động",
                    "user_id": "user123",
                    "k": 5,
                }
            ]
        }
    }


class RerankRequest(BaseModel):
    """Request for LLM-based document reranking."""

    query: str = Field(
        ...,
        min_length=1,
        description="Search query for relevance scoring"
    )
    documents: str = Field(
        ...,
        description="JSON string of retrieved documents to rerank"
    )
    top_k: int = Field(
        5,
        ge=1,
        description="Number of top documents to return"
    )
    method: str = Field(
        "llm_rerank",
        description="Reranking method: llm_rerank or score_and_rerank"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "hợp đồng lao động",
                    "documents": '[{"text": "doc1", "metadata": {}}, {"text": "doc2"}]',
                    "top_k": 3,
                    "method": "llm_rerank",
                }
            ]
        }
    }


__all__ = [
    "HybridSearchRequest",
    "DenseSearchRequest",
    "BM25SearchRequest",
    "RerankRequest",
]
