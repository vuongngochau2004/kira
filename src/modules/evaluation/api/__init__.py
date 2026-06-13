"""
Evaluation API layer.

Contains request/response schemas for evaluation endpoints.
"""

from src.modules.evaluation.api.schemas import (
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    EvaluationMetric,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
    GoldenDataset,
    GoldenDatasetSample,
)

__all__ = [
    "EvaluationMetric",
    "EvaluationRequest",
    "EvaluationResponse",
    "EvaluationResult",
    "BatchEvaluationRequest",
    "BatchEvaluationResponse",
    "GoldenDataset",
    "GoldenDatasetSample",
]
