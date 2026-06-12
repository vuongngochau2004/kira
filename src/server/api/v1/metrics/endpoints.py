"""Metrics API endpoints for routing monitoring and analysis."""

from fastapi import APIRouter, Depends

from src.shared.infrastructure.monitoring.routing_metrics import get_metrics_collector
from src.shared.infrastructure.auth.dependencies import get_current_user
from src.shared.infrastructure.persistence.database.models import User

router = APIRouter()


@router.get("/routing/summary")
async def get_routing_metrics_summary(
    time_window_seconds: int = 3600,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get routing metrics summary.

    Args:
        time_window_seconds: Time window for metrics (default 1 hour)
        current_user: Authenticated user

    Returns:
        Dictionary with routing metrics summary
    """
    collector = get_metrics_collector()
    metrics = collector.get_metrics_summary(time_window_seconds=time_window_seconds)
    return metrics.to_dict()


@router.get("/routing/analysis")
async def get_routing_baseline_analysis(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get baseline analysis for Go/No-Go decision.

    Returns:
        Dictionary with baseline analysis and recommendations
    """
    collector = get_metrics_collector()
    analysis = collector.analyze_baseline()
    return analysis


@router.get("/routing/problematic")
async def get_problematic_queries(
    min_confidence: float = 0.6,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Get queries with low confidence scores.

    Args:
        min_confidence: Minimum confidence threshold
        limit: Maximum number of queries to return
        current_user: Authenticated user

    Returns:
        List of problematic query details
    """
    collector = get_metrics_collector()
    return collector.get_problematic_queries(min_confidence=min_confidence, limit=limit)


@router.get("/routing/hourly")
async def get_hourly_distribution(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get routing method distribution by hour.

    Args:
        hours: Number of hours to analyze
        current_user: Authenticated user

    Returns:
        Dictionary with hourly breakdown of routing methods
    """
    collector = get_metrics_collector()
    return collector.get_hourly_distribution(hours=hours)


@router.post("/routing/clear")
async def clear_old_routing_data(
    retention_seconds: int = 86400,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Clear old routing decision data.

    Args:
        retention_seconds: Data retention period (default 24 hours)
        current_user: Authenticated user

    Returns:
        Dictionary with number of decisions cleared
    """
    collector = get_metrics_collector()
    cleared = collector.clear_old_data(retention_seconds=retention_seconds)
    return {"cleared_decisions": cleared}


__all__ = ["router"]
