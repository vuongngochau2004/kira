"""
API request/response DTOs for evaluation module.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class EvaluationRequestDTO(BaseModel):
    """Request DTO for single evaluation."""

    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    context: str = Field(..., min_length=1, description="Retrieved context")
    answer: str = Field(..., min_length=1, description="Generated answer")
    ground_truth: Optional[str] = Field(None, description="Ground truth answer")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Điều khoản hợp đồng lao động là gì?",
                "context": "Theo Bộ luật Lao động 2019...",
                "answer": "Điều khoản hợp đồng lao động bao gồm...",
                "ground_truth": "Các điều khoản chính trong hợp đồng lao động..."
            }
        }


class EvaluationResponseDTO(BaseModel):
    """Response DTO for evaluation results."""

    faithfulness: float = Field(..., ge=0.0, le=1.0, description="Faithfulness score")
    answer_relevancy: float = Field(..., ge=0.0, le=1.0, description="Answer relevancy score")
    context_precision: float = Field(..., ge=0.0, le=1.0, description="Context precision score")
    context_recall: float = Field(..., ge=0.0, le=1.0, description="Context recall score")
    average_score: float = Field(..., ge=0.0, le=1.0, description="Average score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "faithfulness": 0.85,
                "answer_relevancy": 0.90,
                "context_precision": 0.88,
                "context_recall": 0.75,
                "average_score": 0.845,
                "metadata": {}
            }
        }


class BatchEvaluationRequestDTO(BaseModel):
    """Request DTO for batch evaluation."""

    requests: list[EvaluationRequestDTO] = Field(..., min_items=1, max_items=100)

    class Config:
        json_schema_extra = {
            "example": {
                "requests": [
                    {
                        "query": "Câu hỏi 1",
                        "context": "Context 1",
                        "answer": "Answer 1"
                    },
                    {
                        "query": "Câu hỏi 2",
                        "context": "Context 2",
                        "answer": "Answer 2"
                    }
                ]
            }
        }
