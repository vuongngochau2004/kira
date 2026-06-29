"""DeepEval evaluation service."""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any

from src.modules.evaluation.adapters import DeepEvalLLMAdapter
from src.modules.evaluation.domain.models import (
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    EvaluationMetric,
    EvaluationRequest,
    EvaluationResponse,
    MetricResult,
)
from src.modules.evaluation.metrics import (
    citation_accuracy,
    hit_rate_at_k,
    mean_reciprocal_rank,
    recall_at_k,
    refusal_correctness,
)
from src.shared.ports.llm import LLMPort


class EvaluationError(Exception):
    """Base exception for evaluation failures."""


class DeepEvalEvaluationService:
    """Evaluate RAG outputs with DeepEval plus local deterministic metrics."""

    _RETRIEVAL_METRICS = frozenset(
        {
            EvaluationMetric.HIT_RATE_AT_K,
            EvaluationMetric.MRR,
            EvaluationMetric.RECALL_AT_K,
        }
    )

    def __init__(
        self,
        judge_llm: LLMPort | None = None,
        threshold: float = 0.7,
    ):
        self.judge_llm = judge_llm
        self.threshold = threshold
        self._judge_model = (
            DeepEvalLLMAdapter(judge_llm, model_name="kira-deepeval-judge")
            if judge_llm is not None
            else None
        )

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        """Evaluate one RAG output."""
        started = time.time()
        results: list[MetricResult] = []

        for raw_metric in request.metrics:
            metric = raw_metric.canonical
            if self._should_skip_metric(metric, request):
                continue

            if metric == EvaluationMetric.CITATION_ACCURACY:
                score, reason = citation_accuracy(
                    expected=request.expected_citations,
                    actual=request.actual_citations,
                )
                results.append(self._metric_result(metric, score, reason=reason))
                continue

            if metric == EvaluationMetric.REFUSAL_CORRECTNESS:
                score, reason = await refusal_correctness(
                    answer=request.answer,
                    should_refuse=request.should_refuse,
                    llm=self.judge_llm,
                )
                results.append(self._metric_result(metric, score, reason=reason))
                continue

            if metric in self._RETRIEVAL_METRICS:
                score, reason = self._retrieval_metric(metric, request)
                results.append(self._metric_result(metric, score, reason=reason))
                continue

            try:
                result = await asyncio.to_thread(self._run_deepeval_metric, metric, request)
                results.append(result)
            except Exception as exc:
                results.append(
                    MetricResult(
                        metric=metric,
                        score=0.0,
                        threshold=self.threshold,
                        passed=False,
                        error=str(exc),
                    )
                )

        scored = [result.score for result in results]
        overall = sum(scored) / len(scored) if scored else 0.0
        response_metadata = dict(request.metadata)
        response_metadata["failure_analysis"] = self._failure_analysis(results)

        return EvaluationResponse(
            evaluation_id=str(uuid.uuid4()),
            sample_id=str(request.metadata.get("sample_id") or "") or None,
            query=request.query,
            answer=request.answer,
            results=results,
            overall_score=overall,
            passed=all(item.passed for item in results),
            evaluated_at=datetime.utcnow(),
            duration_seconds=time.time() - started,
            metadata=response_metadata,
        )

    async def evaluate_batch(self, request: BatchEvaluationRequest) -> BatchEvaluationResponse:
        """Evaluate many RAG outputs concurrently with bounded concurrency."""
        batch_id = str(uuid.uuid4())
        started = time.time()
        started_at = datetime.utcnow()
        results: list[EvaluationResponse] = []
        failed = 0

        sem = asyncio.Semaphore(5)  # Restrict to 5 concurrent evaluations

        async def _evaluate_with_semaphore(
            item: EvaluationRequest,
        ) -> tuple[EvaluationResponse | None, bool]:
            async with sem:
                if request.metrics is not None:
                    item.metrics = request.metrics
                try:
                    res = await self.evaluate(item)
                    return res, False
                except Exception:
                    return None, True

        tasks = [_evaluate_with_semaphore(item) for item in request.queries]
        eval_results = await asyncio.gather(*tasks)

        for res, is_fail in eval_results:
            if is_fail or res is None:
                failed += 1
            else:
                results.append(res)

        return BatchEvaluationResponse(
            batch_id=batch_id,
            total_queries=len(request.queries),
            successful_evaluations=len(results),
            failed_evaluations=failed,
            results=results,
            aggregated_scores=self._aggregate(results),
            started_at=started_at,
            completed_at=datetime.utcnow(),
            total_duration_seconds=time.time() - started,
        )

    def _run_deepeval_metric(
        self,
        metric: EvaluationMetric,
        request: EvaluationRequest,
    ) -> MetricResult:
        """Run a DeepEval metric in a worker thread."""
        deepeval_metric = self._build_deepeval_metric(metric)
        test_case = self._build_test_case(request)
        deepeval_metric.measure(test_case)
        score = float(deepeval_metric.score or 0.0)
        reason = getattr(deepeval_metric, "reason", None)
        return self._metric_result(metric, score, reason=reason)

    def _build_deepeval_metric(self, metric: EvaluationMetric) -> Any:
        try:
            from deepeval.metrics import (
                AnswerRelevancyMetric,
                ContextualPrecisionMetric,
                ContextualRecallMetric,
                ContextualRelevancyMetric,
                FaithfulnessMetric,
            )
        except ImportError as exc:
            raise EvaluationError(
                "DeepEval is not installed. Run `uv sync --extra dev` or "
                "`pip install -e '.[dev]'` before running evaluation."
            ) from exc

        kwargs: dict[str, Any] = {"threshold": self.threshold}
        if self._judge_model is not None:
            kwargs["model"] = self._judge_model

        if metric == EvaluationMetric.ANSWER_RELEVANCY:
            return AnswerRelevancyMetric(**kwargs)
        if metric == EvaluationMetric.FAITHFULNESS:
            return FaithfulnessMetric(**kwargs)
        if metric == EvaluationMetric.CONTEXTUAL_PRECISION:
            return ContextualPrecisionMetric(**kwargs)
        if metric == EvaluationMetric.CONTEXTUAL_RECALL:
            return ContextualRecallMetric(**kwargs)
        if metric == EvaluationMetric.CONTEXTUAL_RELEVANCY:
            return ContextualRelevancyMetric(**kwargs)

        raise EvaluationError(f"Unsupported DeepEval metric: {metric.value}")

    def _build_test_case(self, request: EvaluationRequest) -> Any:
        try:
            from deepeval.test_case import LLMTestCase
        except ImportError as exc:
            raise EvaluationError(
                "DeepEval is not installed. Run `uv sync --extra dev` or "
                "`pip install -e '.[dev]'` before running evaluation."
            ) from exc

        return LLMTestCase(
            input=request.query,
            actual_output=request.answer,
            expected_output=request.expected_answer,
            retrieval_context=request.generation_contexts or request.contexts,
            context=request.reference_contexts or request.generation_contexts or request.contexts,
        )

    def _metric_result(
        self,
        metric: EvaluationMetric,
        score: float,
        reason: str | None = None,
    ) -> MetricResult:
        bounded = max(0.0, min(1.0, score))
        return MetricResult(
            metric=metric,
            score=bounded,
            threshold=self.threshold,
            passed=bounded >= self.threshold,
            reason=reason,
        )

    @staticmethod
    def _retrieval_metric(
        metric: EvaluationMetric,
        request: EvaluationRequest,
    ) -> tuple[float, str]:
        expected = request.metadata.get("expected_context_ids", [])
        retrieved = request.metadata.get("retrieved_context_ids", [])
        if expected and retrieved:
            if metric == EvaluationMetric.HIT_RATE_AT_K:
                return hit_rate_at_k(expected, retrieved, request.retrieval_k)
            if metric == EvaluationMetric.MRR:
                return mean_reciprocal_rank(expected, retrieved)
            if metric == EvaluationMetric.RECALL_AT_K:
                return recall_at_k(expected, retrieved, request.retrieval_k)

        if request.reference_contexts and request.contexts:
            from src.modules.evaluation.metrics import (
                hit_rate_at_k_text,
                mean_reciprocal_rank_text,
                recall_at_k_text,
            )

            if metric == EvaluationMetric.HIT_RATE_AT_K:
                return hit_rate_at_k_text(
                    request.reference_contexts, request.contexts, request.retrieval_k
                )
            if metric == EvaluationMetric.MRR:
                return mean_reciprocal_rank_text(request.reference_contexts, request.contexts)
            if metric == EvaluationMetric.RECALL_AT_K:
                return recall_at_k_text(
                    request.reference_contexts, request.contexts, request.retrieval_k
                )

        if metric == EvaluationMetric.HIT_RATE_AT_K:
            return hit_rate_at_k(expected, retrieved, request.retrieval_k)
        if metric == EvaluationMetric.MRR:
            return mean_reciprocal_rank(expected, retrieved)
        if metric == EvaluationMetric.RECALL_AT_K:
            return recall_at_k(expected, retrieved, request.retrieval_k)
        raise EvaluationError(f"Unsupported retrieval metric: {metric.value}")

    @staticmethod
    def _should_skip_metric(metric: EvaluationMetric, request: EvaluationRequest) -> bool:
        """Skip DeepEval metrics that are not meaningful for refusal samples."""
        if metric in DeepEvalEvaluationService._RETRIEVAL_METRICS and not request.metadata.get(
            "expected_context_ids"
        ):
            return True

        if not request.should_refuse:
            return False

        if metric in {
            EvaluationMetric.CONTEXTUAL_PRECISION,
            EvaluationMetric.CONTEXTUAL_RECALL,
            EvaluationMetric.CONTEXTUAL_RELEVANCY,
        }:
            return True

        return False

    @staticmethod
    def _aggregate(results: list[EvaluationResponse]) -> dict[str, float]:
        scores: dict[str, list[float]] = {}
        for result in results:
            for metric in result.results:
                scores.setdefault(metric.metric.value, []).append(metric.score)
        aggregated = {name: sum(values) / len(values) for name, values in scores.items() if values}
        if results:
            aggregated["overall_score"] = sum(r.overall_score for r in results) / len(results)
            aggregated["pass_rate"] = sum(1 for r in results if r.passed) / len(results)
        return aggregated

    @staticmethod
    def _failure_analysis(results: list[MetricResult]) -> dict[str, Any]:
        """Classify sample failures into actionable RAG subsystem buckets."""
        by_metric = {result.metric.value: result for result in results}
        scores = {name: result.score for name, result in by_metric.items()}

        def failed(metric: str) -> bool:
            result = by_metric.get(metric)
            return bool(result and not result.passed)

        retrieval_metrics = ("mrr", "recall_at_k", "hit_rate_at_k")
        retrieval_failed = any(failed(metric) for metric in retrieval_metrics)
        retrieval_ok = not retrieval_failed
        categories: list[str] = []
        actions: list[str] = []

        if failed("recall_at_k") or failed("hit_rate_at_k"):
            categories.append("retrieval_miss")
            actions.append("Improve indexing, chunk coverage, query rewriting, or retrieval top-k.")
        elif failed("mrr"):
            categories.append("retrieval_ranking")
            actions.append("Tune hybrid weights, candidate pool, or reranker ordering.")

        if failed("contextual_relevancy"):
            categories.append("context_noise")
            actions.append("Tighten reranking, chunk selection, or context compression.")

        if retrieval_ok and failed("answer_relevancy"):
            categories.append("generation_answer")
            actions.append(
                "Make the generation prompt answer the query directly and preserve answer-bearing context."
            )

        if failed("faithfulness"):
            categories.append("generation_grounding")
            actions.append("Strengthen grounding instructions and reduce unsupported synthesis.")

        if failed("citation_accuracy"):
            categories.append("citation_mapping")
            actions.append("Fix citation extraction and source-to-answer mapping.")

        if failed("refusal_correctness"):
            categories.append("refusal_policy")
            actions.append("Tune no-answer detection and refusal wording.")

        if not categories:
            categories.append("passed")
            actions.append("No failed metric in this sample.")

        return {
            "primary_category": categories[0],
            "categories": categories,
            "retrieval_failed": retrieval_failed,
            "generation_failed": any(category.startswith("generation") for category in categories),
            "scores": scores,
            "recommended_actions": actions,
        }


_evaluation_service: DeepEvalEvaluationService | None = None


def get_evaluation_service(judge_llm: LLMPort | None = None) -> DeepEvalEvaluationService:
    """Return a singleton evaluation service for API compatibility."""
    global _evaluation_service
    if _evaluation_service is None or judge_llm is not None:
        _evaluation_service = DeepEvalEvaluationService(judge_llm=judge_llm)
    return _evaluation_service


__all__ = [
    "DeepEvalEvaluationService",
    "EvaluationError",
    "get_evaluation_service",
]
