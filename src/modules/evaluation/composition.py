"""Dependency composition for the evaluation module."""

from src.modules.evaluation.application.use_case import Evaluation
from src.modules.evaluation.domain.dataset import DatasetManager, get_dataset_manager
from src.modules.evaluation.domain.service import DeepEvalEvaluationService, get_evaluation_service


def evaluation_service() -> DeepEvalEvaluationService:
    """Return the configured DeepEval evaluation service."""
    return get_evaluation_service()


def dataset_manager() -> DatasetManager:
    """Return the configured golden dataset manager."""
    return get_dataset_manager()


def evaluation_use_case(service: DeepEvalEvaluationService | None = None) -> Evaluation:
    """Compose the evaluation application use case."""
    return Evaluation(service=service or evaluation_service())


__all__ = ["dataset_manager", "evaluation_service", "evaluation_use_case"]
