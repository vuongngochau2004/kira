"""DeepEval evaluation API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.modules.evaluation.composition import dataset_manager, evaluation_service
from src.modules.evaluation.api.schemas import (
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    EvaluationRequest,
    EvaluationResponse,
    GoldenDataset,
)
from src.shared.infrastructure.auth.dependencies import get_current_user
from src.shared.infrastructure.persistence.database.models import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_rag_output(
    request: EvaluationRequest,
    current_user: User = Depends(get_current_user),
) -> EvaluationResponse:
    """Evaluate one generated RAG answer with DeepEval metrics."""
    try:
        result = await evaluation_service().evaluate(request)
        logger.info(
            "[DEEPEVAL] user=%s query='%s...' overall=%.2f",
            current_user.id,
            request.query[:50],
            result.overall_score,
        )
        return result
    except Exception as exc:
        logger.error("DeepEval single evaluation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/evaluate/batch", response_model=BatchEvaluationResponse)
async def evaluate_batch(
    request: BatchEvaluationRequest,
    current_user: User = Depends(get_current_user),
) -> BatchEvaluationResponse:
    """Evaluate multiple already-generated RAG answers."""
    try:
        result = await evaluation_service().evaluate_batch(request)
        logger.info(
            "[DEEPEVAL] user=%s batch=%s pass_rate=%.2f",
            current_user.id,
            result.batch_id,
            result.aggregated_scores.get("pass_rate", 0.0),
        )
        return result
    except Exception as exc:
        logger.error("DeepEval batch evaluation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/datasets", response_model=list[GoldenDataset])
async def list_golden_datasets(
    current_user: User = Depends(get_current_user),
) -> list[GoldenDataset]:
    """List local golden datasets."""
    try:
        return dataset_manager().list_datasets()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/datasets", response_model=GoldenDataset, status_code=status.HTTP_201_CREATED)
async def create_golden_dataset(
    dataset: GoldenDataset,
    current_user: User = Depends(get_current_user),
) -> GoldenDataset:
    """Save a local golden dataset."""
    try:
        dataset_manager().save_dataset(dataset)
        return dataset
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
