"""DeepEval-backed evaluation models for RAG benchmarks."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EvaluationMetric(str, Enum):
    """Metrics supported by the local DeepEval runner."""

    ANSWER_RELEVANCY = "answer_relevancy"
    FAITHFULNESS = "faithfulness"
    CONTEXTUAL_PRECISION = "contextual_precision"
    CONTEXTUAL_RECALL = "contextual_recall"
    CONTEXTUAL_RELEVANCY = "contextual_relevancy"
    HIT_RATE_AT_K = "hit_rate_at_k"
    MRR = "mrr"
    RECALL_AT_K = "recall_at_k"
    CITATION_ACCURACY = "citation_accuracy"
    REFUSAL_CORRECTNESS = "refusal_correctness"

    # Backward-compatible spelling used by older evaluation clients.
    CONTEXT_PRECISION = "context_precision"
    CONTEXT_RECALL = "context_recall"

    @property
    def canonical(self) -> "EvaluationMetric":
        """Return the DeepEval-oriented canonical metric name."""
        if self == EvaluationMetric.CONTEXT_PRECISION:
            return EvaluationMetric.CONTEXTUAL_PRECISION
        if self == EvaluationMetric.CONTEXT_RECALL:
            return EvaluationMetric.CONTEXTUAL_RECALL
        return self


DEFAULT_METRICS = [
    EvaluationMetric.ANSWER_RELEVANCY,
    EvaluationMetric.FAITHFULNESS,
    EvaluationMetric.CONTEXTUAL_RECALL,
]


class EvaluationRequest(BaseModel):
    """Evaluate one already-generated RAG output."""

    query: str = Field(..., min_length=1, max_length=5000)
    answer: str = Field(..., min_length=1, max_length=20000)
    contexts: list[str] = Field(default_factory=list, max_length=100)
    generation_contexts: list[str] = Field(default_factory=list, max_length=100)
    expected_answer: str | None = None
    reference_contexts: list[str] = Field(default_factory=list)
    expected_citations: list[str] = Field(default_factory=list)
    actual_citations: list[str] = Field(default_factory=list)
    should_refuse: bool = False
    retrieval_k: int = Field(default=5, ge=1, le=100)
    metrics: list[EvaluationMetric] = Field(default_factory=lambda: DEFAULT_METRICS.copy())
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("contexts", "generation_contexts", "reference_contexts")
    @classmethod
    def strip_empty_contexts(cls, value: list[str]) -> list[str]:
        """Drop empty context strings before sending data to DeepEval."""
        return [item.strip() for item in value if item and item.strip()]


class MetricResult(BaseModel):
    """Result for one metric on one sample."""

    metric: EvaluationMetric
    score: float = Field(..., ge=0.0, le=1.0)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    passed: bool
    reason: str | None = None
    error: str | None = None


class EvaluationResponse(BaseModel):
    """Evaluation result for one sample."""

    evaluation_id: str
    sample_id: str | None = None
    query: str
    answer: str
    results: list[MetricResult]
    overall_score: float = Field(..., ge=0.0, le=1.0)
    passed: bool
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchEvaluationRequest(BaseModel):
    """Evaluate many already-generated RAG outputs."""

    queries: list[EvaluationRequest] = Field(..., min_length=1, max_length=200)
    metrics: list[EvaluationMetric] | None = None
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class BatchEvaluationResponse(BaseModel):
    """Batch evaluation response with aggregate scores."""

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
    """One benchmark sample for running the real RAG pipeline."""

    id: str
    query: str
    expected_answer: str | None = None
    reference_contexts: list[str] = Field(default_factory=list)
    expected_context_ids: list[str] = Field(default_factory=list)
    expected_citations: list[str] = Field(default_factory=list)
    should_refuse: bool = False
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GoldenDataset(BaseModel):
    """Golden dataset stored as JSON."""

    dataset_id: str
    name: str
    description: str | None = None
    samples: list[GoldenDatasetSample]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None


class EvaluationRunConfig(BaseModel):
    """Runtime configuration for a benchmark run."""

    dataset_path: str
    output_dir: str = "reports/evaluation"
    user_id: str
    metrics: list[EvaluationMetric] = Field(default_factory=lambda: DEFAULT_METRICS.copy())
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    retrieval_k: int = Field(default=5, ge=1, le=100)
    max_samples: int | None = Field(default=None, ge=1)
    run_name: str | None = None


class EvaluationHistory(BaseModel):
    """Compact history entry used by API compatibility surfaces."""

    evaluation_id: str
    query: str
    metrics: dict[str, float]
    overall_score: float
    evaluated_at: datetime
    duration_seconds: float


__all__ = [
    "DEFAULT_METRICS",
    "EvaluationMetric",
    "EvaluationRequest",
    "EvaluationResponse",
    "MetricResult",
    "BatchEvaluationRequest",
    "BatchEvaluationResponse",
    "GoldenDataset",
    "GoldenDatasetSample",
    "EvaluationRunConfig",
    "EvaluationHistory",
]
