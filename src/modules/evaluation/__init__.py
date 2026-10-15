"""Evaluation module for RAG benchmark and regression testing.

The previous prompt-based evaluator has been replaced by DeepEval-backed runners.
Use the CLI with `python -m src.modules.evaluation.cli run ...` for offline
benchmarking and report generation.
"""

from src.modules.evaluation.application import Evaluation, EvaluationQuery, EvaluationResultDTO
from src.modules.evaluation.domain import (
    DatasetManager,
    DeepEvalEvaluationService,
    EvaluationError,
    EvaluationMetric,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationRunConfig,
    GoldenDataset,
    GoldenDatasetSample,
    get_dataset_manager,
    get_evaluation_service,
)

__all__ = [
    "DatasetManager",
    "DeepEvalEvaluationService",
    "Evaluation",
    "EvaluationError",
    "EvaluationMetric",
    "EvaluationQuery",
    "EvaluationRequest",
    "EvaluationResponse",
    "EvaluationResultDTO",
    "EvaluationRunConfig",
    "GoldenDataset",
    "GoldenDatasetSample",
    "get_dataset_manager",
    "get_evaluation_service",
]
