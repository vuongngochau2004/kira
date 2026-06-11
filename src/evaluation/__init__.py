"""RAGAS evaluation package."""

from evaluation.service import (
    RAGASEvaluationService,
    get_evaluation_service,
    EvaluationError,
)

__all__ = [
    "RAGASEvaluationService",
    "get_evaluation_service",
    "EvaluationError",
]
