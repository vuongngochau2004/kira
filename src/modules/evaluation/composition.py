"""Dependency composition for the evaluation module."""

from src.modules.evaluation.application.use_case import Evaluation
from src.modules.evaluation.domain.dataset import DatasetManager, get_dataset_manager
from src.modules.evaluation.domain.framework import RAGEvaluationFramework
from src.modules.evaluation.domain.service import RAGASEvaluationService, get_evaluation_service


def evaluation_service() -> RAGASEvaluationService:
    """Return the configured RAGAS evaluation service."""
    return get_evaluation_service()


def dataset_manager() -> DatasetManager:
    """Return the configured golden dataset manager."""
    return get_dataset_manager()


def evaluation_use_case(
    service: RAGASEvaluationService | None = None,
    framework: RAGEvaluationFramework | None = None,
) -> Evaluation:
    """Compose the evaluation application use case."""
    return Evaluation(
        service=service or evaluation_service(),
        framework=framework,
    )


__all__ = [
    "dataset_manager",
    "evaluation_service",
    "evaluation_use_case",
]
