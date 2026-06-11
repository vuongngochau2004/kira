"""
Evaluation domain layer.

Contains RAG evaluation business logic using RAGAS metrics.
"""

from src.modules.evaluation.domain.service import RAGASEvaluationService, get_evaluation_service, EvaluationError
from src.modules.evaluation.domain.framework import RAGEvaluationFramework, MetricType, AgentMetric, GraphMetric

__all__ = [
    # Service
    "RAGASEvaluationService",
    "get_evaluation_service",
    "EvaluationError",
    # Framework
    "RAGEvaluationFramework",
    "MetricType",
    "AgentMetric",
    "GraphMetric",
]

