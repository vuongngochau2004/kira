"""
Evaluation use case for RAG pipeline assessment.

Orchestrates RAGAS evaluation service for quality assessment.
"""

import logging
from typing import Any

from src.modules.evaluation.domain.service import RAGASEvaluationService, get_evaluation_service
from src.modules.evaluation.domain.framework import RAGEvaluationFramework

logger = logging.getLogger(__name__)


class EvaluationUseCase:
    """
    Use case for RAG pipeline evaluation.

    Orchestrates evaluation service and framework for comprehensive
    RAG quality assessment using RAGAS metrics.

    Attributes:
        service: RAGAS evaluation service
        framework: Evaluation framework (optional)

    Example:
        >>> use_case = EvaluationUseCase()
        >>> results = await use_case.evaluate_rag_pipeline(
        ...     queries=test_queries,
        ...     rag_pipeline=rag_handler
        ... )
    """

    def __init__(
        self,
        service: RAGASEvaluationService | None = None,
        framework: RAGEvaluationFramework | None = None
    ):
        """
        Initialize evaluation use case.

        Args:
            service: Custom evaluation service (creates default if None)
            framework: Custom evaluation framework (optional)
        """
        self.service = service or get_evaluation_service()
        self.framework = framework

    async def evaluate(
        self,
        query: str,
        context: str,
        answer: str,
        ground_truth: str | None = None
    ) -> dict[str, Any]:
        """
        Evaluate single RAG result.

        Args:
            query: User query
            context: Retrieved context
            answer: Generated answer
            ground_truth: Ground truth answer (optional)

        Returns:
            Dict with evaluation metrics
        """
        from models.evaluation import EvaluationRequest

        request = EvaluationRequest(
            query=query,
            contexts=[context],
            answer=answer,
            ground_truth=ground_truth
        )

        result = await self.service.evaluate(request)

        return {
            "faithfulness": result.metrics.get("faithfulness", 0.0),
            "answer_relevancy": result.metrics.get("answer_relevancy", 0.0),
            "context_precision": result.metrics.get("context_precision", 0.0),
            "context_recall": result.metrics.get("context_recall", 0.0),
        }

    async def evaluate_batch(
        self,
        requests: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Evaluate multiple RAG results.

        Args:
            requests: List of evaluation request dicts

        Returns:
            List of evaluation result dicts
        """
        from models.evaluation import BatchEvaluationRequest, EvaluationRequest

        eval_requests = [
            EvaluationRequest(
                query=req["query"],
                contexts=req.get("contexts", []),
                answer=req["answer"],
                ground_truth=req.get("ground_truth")
            )
            for req in requests
        ]

        batch_request = BatchEvaluationRequest(requests=eval_requests)
        result = await self.service.evaluate_batch(batch_request)

        return [
            {
                "query": r.query,
                "faithfulness": r.metrics.get("faithfulness", 0.0),
                "answer_relevancy": r.metrics.get("answer_relevancy", 0.0),
            }
            for r in result.results
        ]

    def get_service_info(self) -> dict[str, Any]:
        """
        Get evaluation service information.

        Returns:
            Dict with service configuration
        """
        return {
            "cache_enabled": self.service.cache_enabled,
            "timeout_seconds": self.service.timeout_seconds,
            "cache_size": len(self.service._cache)
        }
