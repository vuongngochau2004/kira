"""
API request DTOs for classification module.

Defines request models for classification endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Any, Optional
from uuid import UUID


class ClassifyRequest(BaseModel):
    """
    Request DTO for query classification.

    Attributes:
        query: User query string to classify
        user_id: User ID making the query
        context: Additional context (conversation history, etc.)
    """

    query: str = Field(..., min_length=1, max_length=2000, description="User query to classify")
    user_id: str = Field(..., min_length=1, max_length=100, description="User ID")
    context: Optional[dict[str, Any]] = Field(default=None, description="Additional context")

    @validator("query")
    def validate_query(cls, v):
        """Validate query is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()

    @validator("user_id")
    def validate_user_id(cls, v):
        """Validate user_id is not empty."""
        if not v or not v.strip():
            raise ValueError("User ID cannot be empty")
        return v

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "query": "hỏi về điều khoản hợp đồng lao động",
                "user_id": "user123",
                "context": {"conversation_id": "conv-456"}
            }
        }


class BatchClassifyRequest(BaseModel):
    """
    Request DTO for batch classification.

    Attributes:
        queries: List of query classification requests
    """

    queries: list[ClassifyRequest] = Field(..., min_items=1, max_items=50, description="List of queries to classify")

    @validator("queries")
    def validate_queries(cls, v):
        """Validate queries list is not empty."""
        if not v:
            raise ValueError("Queries list cannot be empty")
        return v

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "queries": [
                    {"query": "xin chào", "user_id": "user123"},
                    {"query": "điều khoản hợp đồng", "user_id": "user123"}
                ]
            }
        }
