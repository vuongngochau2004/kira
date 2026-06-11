"""RAGAS evaluation API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.persistence.database.session import get_session
from src.models.evaluation import (
    EvaluationRequest,
    EvaluationResponse,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    GoldenDataset,
)
from src.modules.evaluation.domain.service import get_evaluation_service, RAGASEvaluationService
from src.modules.evaluation.domain.dataset import get_dataset_manager
from src.shared.infrastructure.auth.dependencies import get_current_user
from src.shared.infrastructure.persistence.database.models import User
from src.config.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_rag_output(
    request: EvaluationRequest,
    current_user: User = Depends(get_current_user),
) -> EvaluationResponse:
    """Evaluate a single RAG output.

    Request body:
    {
        "query": "user question",
        "answer": "generated answer",
        "contexts": ["context1", "context2", ...],
        "metrics": ["faithfulness", "answer_relevancy"]
    }

    Returns:
        EvaluationResponse with scores for each metric
    """
    if not settings.ragas_evaluation_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAGAS evaluation is disabled",
        )

    try:
        service = get_evaluation_service()
        result = await service.evaluate(request)

        logger.info(
            f"[EVAL API] User {current_user.id} evaluated query "
            f"'{request.query[:50]}...', score={result.overall_score:.2f}"
        )

        return result

    except Exception as e:
        logger.error(f"[EVAL API] Evaluation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/evaluate/batch", response_model=BatchEvaluationResponse)
async def evaluate_batch(
    request: BatchEvaluationRequest,
    current_user: User = Depends(get_current_user),
) -> BatchEvaluationResponse:
    """Evaluate multiple RAG outputs in batch.

    Request body:
    {
        "queries": [
            {"query": "...", "answer": "...", "contexts": [...]},
            ...
        ],
        "metrics": ["faithfulness", "answer_relevancy"],
        "concurrent_evaluations": 10
    }

    Returns:
        BatchEvaluationResponse with aggregated scores
    """
    if not settings.ragas_evaluation_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAGAS evaluation is disabled",
        )

    try:
        service = get_evaluation_service()
        result = await service.evaluate_batch(request)

        logger.info(
            f"[EVAL API] User {current_user.id} completed batch {result.batch_id}: "
            f"{result.successful_evaluations}/{result.total_queries} successful"
        )

        return result

    except Exception as e:
        logger.error(f"[EVAL API] Batch evaluation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/evaluate/datasets", response_model=list[GoldenDataset])
async def list_golden_datasets(
    current_user: User = Depends(get_current_user),
) -> list[GoldenDataset]:
    """List available golden datasets for validation."""
    try:
        manager = get_dataset_manager()
        datasets = manager.list_datasets()
        return datasets
    except Exception as e:
        logger.error(f"[EVAL API] Failed to list datasets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/evaluate/datasets", response_model=GoldenDataset, status_code=status.HTTP_201_CREATED)
async def create_golden_dataset(
    dataset: GoldenDataset,
    current_user: User = Depends(get_current_user),
) -> GoldenDataset:
    """Create a new golden dataset."""
    try:
        manager = get_dataset_manager()
        result = manager.save_dataset(dataset, user_id=str(current_user.id))
        return result
    except Exception as e:
        logger.error(f"[EVAL API] Failed to create dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/evaluate/datasets/{dataset_id}/evaluate", response_model=BatchEvaluationResponse)
async def evaluate_dataset(
    dataset_id: str,
    metrics: Optional[list[str]] = None,
    current_user: User = Depends(get_current_user),
) -> BatchEvaluationResponse:
    """Evaluate a golden dataset.

    Args:
        dataset_id: Dataset ID to evaluate
        metrics: Optional list of metrics (defaults to all)
        current_user: Authenticated user

    Returns:
        BatchEvaluationResponse with dataset evaluation results
    """
    try:
        manager = get_dataset_manager()
        dataset = manager.load_dataset(dataset_id)

        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found",
            )

        # Convert dataset samples to evaluation queries
        queries = [
            {
                "query": sample.query,
                "answer": sample.answer,
                "contexts": sample.contexts,
            }
            for sample in dataset.samples
        ]

        batch_request = BatchEvaluationRequest(
            dataset_id=dataset_id,
            queries=queries,
            metrics=metrics or ["faithfulness", "answer_relevancy", "context_precision"],
        )

        service = get_evaluation_service()
        result = await service.evaluate_batch(batch_request)

        logger.info(
            f"[EVAL API] Evaluated dataset {dataset_id}: "
            f"{result.successful_evaluations}/{result.total_queries} successful"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EVAL API] Dataset evaluation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/evaluate/cache")
async def clear_evaluation_cache(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Clear evaluation result cache."""
    try:
        service = get_evaluation_service()
        cleared = service.clear_cache()
        return {"cleared_entries": cleared}
    except Exception as e:
        logger.error(f"[EVAL API] Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


__all__ = ["router"]
