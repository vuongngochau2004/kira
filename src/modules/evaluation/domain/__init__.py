"""Evaluation domain layer powered by DeepEval."""

from src.modules.evaluation.domain.dataset import DatasetManager, get_dataset_manager
from src.modules.evaluation.domain.models import (
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    DEFAULT_METRICS,
    EvaluationHistory,
    EvaluationMetric,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationRunConfig,
    GoldenDataset,
    GoldenDatasetSample,
    MetricResult,
)
from src.modules.evaluation.domain.service import (
    DeepEvalEvaluationService,
    EvaluationError,
    get_evaluation_service,
)

__all__ = [
    "BatchEvaluationRequest",
    "BatchEvaluationResponse",
    "DEFAULT_METRICS",
    "DatasetManager",
    "DeepEvalEvaluationService",
    "EvaluationError",
    "EvaluationHistory",
    "EvaluationMetric",
    "EvaluationRequest",
    "EvaluationResponse",
    "EvaluationRunConfig",
    "GoldenDataset",
    "GoldenDatasetSample",
    "MetricResult",
    "get_dataset_manager",
    "get_evaluation_service",
]
