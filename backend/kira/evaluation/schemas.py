"""HTTP schemas for evaluation APIs."""

from kira.evaluation.models import (
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    EvaluationHistory,
    EvaluationMetric,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationRunConfig,
    GoldenDataset,
    GoldenDatasetSample,
    MetricResult,
)

EvaluationResult = MetricResult

__all__ = [
    "EvaluationMetric",
    "EvaluationRequest",
    "EvaluationResponse",
    "EvaluationResult",
    "MetricResult",
    "BatchEvaluationRequest",
    "BatchEvaluationResponse",
    "GoldenDataset",
    "GoldenDatasetSample",
    "EvaluationRunConfig",
    "EvaluationHistory",
]
