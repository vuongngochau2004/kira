"""
Evaluation module for RAG pipeline quality assessment.

This module provides RAGAS-based evaluation for RAG outputs including:
- Faithfulness scoring
- Answer relevancy
- Context precision/recall
- Batch evaluation

Usage:
    >>> from src.modules.evaluation import EvaluationUseCase
    >>> use_case = EvaluationUseCase()
    >>> result = await use_case.evaluate(query, context, answer)

Module Structure:
- application/ - Use cases and DTOs
- domain/ - Business logic (RAGAS service, framework)
- infrastructure/ - External adapters (empty for now)
- api/ - Request/response DTOs
"""

from src.modules.evaluation.application import EvaluationUseCase, EvaluationQuery, EvaluationResultDTO
from src.modules.evaluation.domain import (
    RAGASEvaluationService,
    get_evaluation_service,
    EvaluationError,
    RAGEvaluationFramework,
    MetricType,
)
from src.modules.evaluation.api import EvaluationRequestDTO, EvaluationResponseDTO

__all__ = [
    # Application
    "EvaluationUseCase",
    "EvaluationQuery",
    "EvaluationResultDTO",
    # Domain
    "RAGASEvaluationService",
    "get_evaluation_service",
    "EvaluationError",
    "RAGEvaluationFramework",
    "MetricType",
    # API
    "EvaluationRequestDTO",
    "EvaluationResponseDTO",
]
