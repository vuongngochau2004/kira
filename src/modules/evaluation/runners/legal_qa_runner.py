"""Run the legal QA use case against a legal golden dataset."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol

from src.modules.evaluation.domain.legal_dataset import LegalGoldenSample, load_legal_dataset
from src.modules.evaluation.domain.models import (
    DEFAULT_LEGAL_METRICS,
    BatchEvaluationResponse,
    EvaluationMetric,
    EvaluationRequest,
    EvaluationResponse,
    MetricResult,
)
from src.modules.evaluation.domain.service import DeepEvalEvaluationService
from src.modules.evaluation.metrics import cited_sources
from src.modules.evaluation.reports.reporter import EvaluationReporter
from src.modules.legal.application.answer_question import LegalQAResult, LegalQAToken

logger = logging.getLogger(__name__)

# DeepEval metrics that need retrieved contexts; meaningless (and failing) without any.
_CONTEXT_METRICS = frozenset(
    {
        EvaluationMetric.FAITHFULNESS,
        EvaluationMetric.CONTEXTUAL_PRECISION,
        EvaluationMetric.CONTEXTUAL_RECALL,
        EvaluationMetric.CONTEXTUAL_RELEVANCY,
    }
)


class LegalAnswerService(Protocol):
    def stream(self, question: str) -> AsyncIterator[Any]: ...


@dataclass
class PinnedClock:
    """A mutable 'today' so each sample is answered as of its own date."""

    day: date

    def __call__(self) -> date:
        return self.day


@dataclass
class LegalEvaluationRunConfig:
    dataset_path: str
    output_dir: str = "reports/evaluation"
    metrics: list[EvaluationMetric] = field(default_factory=lambda: list(DEFAULT_LEGAL_METRICS))
    threshold: float = 0.7
    max_samples: int | None = None
    run_name: str | None = None


class LegalQAEvaluationRunner:
    def __init__(
        self,
        answer_factory: Callable[[Callable[[], date]], LegalAnswerService],
        evaluator: DeepEvalEvaluationService,
        reporter: EvaluationReporter | None = None,
    ) -> None:
        self._answer_factory = answer_factory
        self._evaluator = evaluator
        self._reporter = reporter or EvaluationReporter()

    async def run(
        self, config: LegalEvaluationRunConfig
    ) -> tuple[BatchEvaluationResponse, dict[str, Path]]:
        dataset = load_legal_dataset(config.dataset_path)
        samples = dataset.samples[: config.max_samples] if config.max_samples else dataset.samples
        clock = PinnedClock(date.today())
        service = self._answer_factory(clock)
        started = time.time()
        started_at = datetime.utcnow()
        results: list[EvaluationResponse] = []
        failed = 0

        for sample in samples:  # sequential: one pinned "today" at a time
            clock.day = sample.today
            try:
                request = await self._request_for(service, sample, config.metrics)
                results.append(await self._evaluator.evaluate(request))
            except Exception as exc:
                logger.exception("Legal evaluation sample %s failed", sample.id)
                results.append(self._failure_result(sample, exc, config))
                failed += 1

        report = BatchEvaluationResponse(
            batch_id=str(uuid.uuid4()),
            total_queries=len(samples),
            successful_evaluations=len(results) - failed,
            failed_evaluations=failed,
            results=results,
            aggregated_scores=DeepEvalEvaluationService._aggregate(results),
            started_at=started_at,
            completed_at=datetime.utcnow(),
            total_duration_seconds=time.time() - started,
        )
        run_name = config.run_name or datetime.utcnow().strftime("legal-eval-%Y%m%d-%H%M%S")
        paths = self._reporter.write(report, output_dir=config.output_dir, run_name=run_name)
        return report, paths

    async def _request_for(
        self,
        service: LegalAnswerService,
        sample: LegalGoldenSample,
        metrics: list[EvaluationMetric],
    ) -> EvaluationRequest:
        parts: list[str] = []
        result: LegalQAResult | None = None
        async for event in service.stream(sample.query):
            if isinstance(event, LegalQAToken):
                parts.append(event.text)
            elif isinstance(event, LegalQAResult):
                result = event
        if result is None:
            raise RuntimeError("Legal QA finished without a result")

        answer = "".join(parts)
        sources = result.citations
        # Faithfulness is judged on everything the LLM saw; citation metrics on what it cited.
        cited = cited_sources(answer, sources)
        contexts = [str(c["text"]) for c in sources if c.get("text")]
        usable = [
            m
            for m in metrics
            if (contexts or m.canonical not in _CONTEXT_METRICS)
            and not (sample.should_refuse and m.canonical == EvaluationMetric.ANSWER_RELEVANCY)
        ]
        return EvaluationRequest(
            query=sample.query,
            answer=answer,
            contexts=contexts,
            expected_answer=sample.expected_answer,
            should_refuse=sample.should_refuse,
            metrics=usable,
            metadata={
                "sample_id": sample.id,
                "category": sample.category,
                "tags": [sample.category],
                "legal_expected": {
                    "mode": sample.expected_mode,
                    "dates": [day.isoformat() for day in sample.expected_dates],
                    "provisions": [p.model_dump(mode="json") for p in sample.expected_provisions],
                },
                "legal_actual": {
                    "mode": result.temporal.mode,
                    "dates": [day.isoformat() for day in result.temporal.dates],
                    "citations": cited,
                    "sources": sources,
                    "notices": result.notices,
                },
            },
        )

    @staticmethod
    def _failure_result(
        sample: LegalGoldenSample, exc: Exception, config: LegalEvaluationRunConfig
    ) -> EvaluationResponse:
        return EvaluationResponse(
            evaluation_id=str(uuid.uuid4()),
            sample_id=sample.id,
            query=sample.query,
            answer=f"Legal QA failed: {exc}",
            results=[
                MetricResult(
                    metric=metric.canonical,
                    score=0.0,
                    threshold=config.threshold,
                    passed=False,
                    error=str(exc),
                )
                for metric in config.metrics
            ],
            overall_score=0.0,
            passed=False,
            metadata={
                "sample_id": sample.id,
                "category": sample.category,
                "pipeline_error": str(exc),
            },
        )
