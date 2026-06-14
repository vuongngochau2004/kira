"""Application use case for DeepEval-backed RAG evaluation."""

from typing import Any

from src.modules.evaluation.domain.models import (
    BatchEvaluationRequest,
    EvaluationRequest,
)
from src.modules.evaluation.domain.service import (
    DeepEvalEvaluationService,
    get_evaluation_service,
)


class Evaluation:
    """Evaluate generated RAG outputs."""

    def __init__(self, service: DeepEvalEvaluationService | None = None):
        self.service = service or get_evaluation_service()

    async def evaluate(
        self,
        query: str,
        context: str,
        answer: str,
        ground_truth: str | None = None,
    ) -> dict[str, Any]:
        request = EvaluationRequest(
            query=query,
            contexts=[context],
            answer=answer,
            expected_answer=ground_truth,
        )
        result = await self.service.evaluate(request)
        scores = {item.metric.value: item.score for item in result.results}
        return {
            **scores,
            "overall_score": result.overall_score,
            "passed": result.passed,
        }

    async def evaluate_batch(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        batch_request = BatchEvaluationRequest(
            queries=[EvaluationRequest(**request) for request in requests]
        )
        result = await self.service.evaluate_batch(batch_request)
        return [
            {
                "query": item.query,
                "overall_score": item.overall_score,
                "passed": item.passed,
                "scores": {metric.metric.value: metric.score for metric in item.results},
            }
            for item in result.results
        ]

    def get_service_info(self) -> dict[str, Any]:
        return {
            "framework": "deepeval",
            "threshold": self.service.threshold,
            "uses_project_judge_llm": self.service.judge_llm is not None,
        }
