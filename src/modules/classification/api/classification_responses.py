"""
API response DTOs for classification module.

Defines response models for classification endpoints.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional
from enum import Enum


class IntentEnum(str, Enum):
    """Intent enum for API responses."""

    RAG = "rag"
    CONVERSATIONAL = "conversational"
    DRAFTING = "drafting"
    SEMANTIC = "semantic"


class ClassificationResponse(BaseModel):
    """
    Response DTO for query classification.

    Attributes:
        intent: Detected intent
        confidence: Classification confidence (0.0 to 1.0)
        reason: Human-readable explanation
        metadata: Additional metadata
        handler_hint: Suggested handler for this intent
    """

    intent: IntentEnum = Field(..., description="Detected intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    reason: str = Field(..., description="Human-readable explanation")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    handler_hint: Optional[str] = Field(None, description="Suggested handler name")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "intent": "rag",
                "confidence": 0.95,
                "reason": "Fuzzy filename match: contract.pdf",
                "metadata": {
                    "strategy": "keyword",
                    "matched_file": "contract.pdf",
                    "cached": False
                },
                "handler_hint": "RAGHandler"
            }
        }


class BatchClassificationResponse(BaseModel):
    """
    Response DTO for batch classification.

    Attributes:
        results: List of classification results
        total: Total number of results
        high_confidence_count: Number of high confidence results (>0.7)
        rag_count: Number of RAG intents
        conversational_count: Number of CONVERSATIONAL intents
    """

    results: list[ClassificationResponse] = Field(..., description="Classification results")
    total: int = Field(..., ge=0, description="Total number of results")
    high_confidence_count: int = Field(..., ge=0, description="High confidence results count")
    rag_count: int = Field(..., ge=0, description="RAG intent count")
    conversational_count: int = Field(..., ge=0, description="CONVERSATIONAL intent count")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "intent": "conversational",
                        "confidence": 0.85,
                        "reason": "Keyword detected: xin chào",
                        "metadata": {"strategy": "keyword"},
                        "handler_hint": "ConversationalHandler"
                    },
                    {
                        "intent": "rag",
                        "confidence": 0.95,
                        "reason": "Fuzzy filename match: contract.pdf",
                        "metadata": {"strategy": "keyword"},
                        "handler_hint": "RAGHandler"
                    }
                ],
                "total": 2,
                "high_confidence_count": 2,
                "rag_count": 1,
                "conversational_count": 1
            }
        }


class StrategyInfoResponse(BaseModel):
    """
    Response DTO for classification strategy information.

    Attributes:
        strategy_count: Number of strategies in chain
        strategy_names: Names of strategies in order
        cache_size: Cache size configuration
    """

    strategy_count: int = Field(..., ge=0, description="Number of strategies")
    strategy_names: list[str] = Field(..., description="Strategy names in order")
    cache_size: int = Field(..., ge=0, description="Cache size")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "strategy_count": 2,
                "strategy_names": ["KeywordStrategy", "CachedStrategy"],
                "cache_size": 1000
            }
        }
