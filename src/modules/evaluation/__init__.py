"""
Evaluation module for RAG pipeline quality assessment.

This module provides RAGAS-based evaluation for RAG outputs including:
- Faithfulness scoring
- Answer relevancy
- Context precision/recall
- Batch evaluation

Usage:
    >>> from src.modules.evaluation import Evaluation
    >>> use_case = Evaluation()
    >>> result = await use_case.evaluate(query, context, answer)

Module Structure:
- application/ - Use cases and DTOs
- domain/ - Business logic (RAGAS service, framework)
- infrastructure/ - External adapters (empty for now)
- api/ - Request/response DTOs
"""

from src.modules.evaluation.application import Evaluation, EvaluationQuery, EvaluationResultDTO
from src.modules.evaluation.domain import (
    RAGASEvaluationService,
    get_evaluation_service,
    EvaluationError,
    RAGEvaluationFramework,
    MetricType,
)
from src.modules.evaluation.api import EvaluationRequest, EvaluationResponse

__all__ = [
    # Application
    "Evaluation",
    "EvaluationQuery",
    "EvaluationResultDTO",
    # Domain
    "RAGASEvaluationService",
    "get_evaluation_service",
    "EvaluationError",
    "RAGEvaluationFramework",
    "MetricType",
    # API
    "EvaluationRequest",
    "EvaluationResponse",
]
