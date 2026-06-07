"""RAGAS evaluation package."""

from src.evaluation.service import (
    RAGASEvaluationService,
    get_evaluation_service,
    EvaluationError,
)

__all__ = [
    "RAGASEvaluationService",
    "get_evaluation_service",
    "EvaluationError",
]
