"""Dependency composition for the evaluation module."""

from src.modules.evaluation.application.use_case import Evaluation
from src.modules.evaluation.domain.dataset import DatasetManager, get_dataset_manager
from src.modules.evaluation.domain.service import DeepEvalEvaluationService, get_evaluation_service
from src.modules.evaluation.infrastructure.ingested_chunk_repository import SqlAlchemyIngestedChunkRepository
from src.shared.infrastructure.persistence.database.session import async_session_factory


def evaluation_service() -> DeepEvalEvaluationService:
    """Return the configured DeepEval evaluation service."""
    return get_evaluation_service()


def dataset_manager() -> DatasetManager:
    """Return the configured golden dataset manager."""
    return get_dataset_manager()


def ingested_chunk_repository() -> SqlAlchemyIngestedChunkRepository:
    """Compose the persistence adapter for evaluation corpus sampling."""
    return SqlAlchemyIngestedChunkRepository(async_session_factory)


def evaluation_use_case(service: DeepEvalEvaluationService | None = None) -> Evaluation:
    """Compose the evaluation application use case."""
    return Evaluation(service=service or evaluation_service())


__all__ = ["dataset_manager", "evaluation_service", "evaluation_use_case", "ingested_chunk_repository"]
