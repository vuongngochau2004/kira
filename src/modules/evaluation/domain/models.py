"""Core evaluation models.

These models describe the evaluation feature itself. API modules may expose
them as HTTP schemas, but domain/application code should import from here
instead of depending on the API layer.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EvaluationMetric(str, Enum):
    """RAGAS evaluation metrics."""

    FAITHFULNESS = "faithfulness"
    ANSWER_RELEVANCY = "answer_relevancy"
    CONTEXT_PRECISION = "context_precision"
    CONTEXT_RECALL = "context_recall"


class EvaluationRequest(BaseModel):
    """Request for evaluating RAG output quality."""

    query: str = Field(..., min_length=1, max_length=5000, description="User's original query")
    answer: str = Field(..., min_length=1, max_length=10000, description="Generated answer to evaluate")
    contexts: list[str] = Field(..., min_length=1, max_length=50, description="Retrieved contexts")
    retrieval_history: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional retrieval history for debugging",
    )
    metrics: list[EvaluationMetric] = Field(
        default=[
            EvaluationMetric.FAITHFULNESS,
            EvaluationMetric.ANSWER_RELEVANCY,
        ],
        description="Metrics to evaluate",
    )

    @field_validator("contexts")
    @classmethod
    def validate_contexts_not_empty(cls, value: list[str]) -> list[str]:
        """Validate that all context strings are non-empty."""
        for index, context in enumerate(value):
            if not context or not context.strip():
                raise ValueError(
                    f"Context at index {index} is empty. All contexts must be non-empty strings."
                )
        return value


class EvaluationResult(BaseModel):
    """Single metric evaluation result."""

    metric: EvaluationMetric
    score: float = Field(..., ge=0.0, le=1.0, description="Evaluation score from 0 to 1")
    reasoning: str | None = Field(default=None, description="LLM's reasoning for the score")
    error: str | None = Field(default=None, description="Error message if evaluation failed")


class EvaluationResponse(BaseModel):
    """Complete evaluation response with all metric scores."""

    evaluation_id: str
    query: str
    results: list[EvaluationResult]
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Average of all metric scores")
    evaluated_at: datetime
    evaluation_duration_seconds: float
    llm_provider: str
    llm_model: str


class BatchEvaluationRequest(BaseModel):
    """Batch evaluation request for multiple queries."""

    dataset_id: str | None = Field(
        default=None,
        description="Optional dataset ID to load from stored datasets",
    )
    queries: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of evaluation queries. Each must have 'query', 'answer', 'contexts'",
    )
    metrics: list[EvaluationMetric] = Field(
        default=[
            EvaluationMetric.FAITHFULNESS,
            EvaluationMetric.ANSWER_RELEVANCY,
            EvaluationMetric.CONTEXT_PRECISION,
            EvaluationMetric.CONTEXT_RECALL,
        ],
        description="Metrics to evaluate for all queries",
    )
    concurrent_evaluations: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Number of concurrent evaluations",
    )


class BatchEvaluationResponse(BaseModel):
    """Batch evaluation response with aggregated results."""

    batch_id: str
    total_queries: int
    successful_evaluations: int
    failed_evaluations: int
    results: list[EvaluationResponse]
    aggregated_scores: dict[str, float]
    started_at: datetime
    completed_at: datetime
    total_duration_seconds: float


class GoldenDatasetSample(BaseModel):
    """Single sample in golden dataset."""

    query: str
    answer: str
    contexts: list[str]
    reference_answer: str | None = Field(
        default=None,
        description="Optional ground truth answer for comparison",
    )
    reference_contexts: list[str] | None = Field(
        default=None,
        description="Optional ground truth contexts for recall evaluation",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata (domain, difficulty, etc.)",
    )


class GoldenDataset(BaseModel):
    """Golden dataset for validation."""

    dataset_id: str
    name: str
    description: str | None = None
    samples: list[GoldenDatasetSample]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None


class EvaluationHistory(BaseModel):
    """Historical evaluation record for tracking."""

    evaluation_id: str
    query: str
    metrics: dict[str, float]
    overall_score: float
    evaluated_at: datetime
    llm_provider: str
    evaluation_duration_seconds: float


__all__ = [
    "EvaluationMetric",
    "EvaluationRequest",
    "EvaluationResponse",
    "EvaluationResult",
    "BatchEvaluationRequest",
    "BatchEvaluationResponse",
    "GoldenDataset",
    "GoldenDatasetSample",
    "EvaluationHistory",
]
