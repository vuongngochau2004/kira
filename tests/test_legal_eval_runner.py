import asyncio
import json
from datetime import date
from pathlib import Path

from src.modules.evaluation.domain.models import EvaluationMetric
from src.modules.evaluation.domain.service import DeepEvalEvaluationService
from src.modules.evaluation.runners.legal_qa_runner import (
    LegalEvaluationRunConfig,
    LegalQAEvaluationRunner,
)
from src.modules.legal.application.answer_question import LegalQAResult, LegalQAToken
from src.modules.legal.domain.temporal import TemporalQuery

DATASET = {
    "dataset_id": "t",
    "name": "t",
    "samples": [
        {
            "id": "current-1",
            "query": "Hiện nay quy định thế nào?",
            "today": "2026-10-15",
            "category": "current",
            "expected_mode": "single",
            "expected_dates": ["2026-10-15"],
            "expected_provisions": [{"provision_key": "1/2099/QH99#D3.K1"}],
        },
        {
            "id": "past-1",
            "query": "Năm 2025 quy định thế nào?",
            "today": "2026-01-10",
            "category": "past",
            "expected_mode": "single",
            "expected_dates": ["2025-12-31"],
            "expected_provisions": [{"provision_key": "1/2099/QH99#D3.K1"}],
        },
        {
            "id": "none-1",
            "query": "Thuế xe máy điện hiện nay?",
            "today": "2026-10-15",
            "category": "no_answer",
            "expected_mode": "single",
            "expected_dates": ["2026-10-15"],
            "should_refuse": True,
        },
        {
            "id": "boom-1",
            "query": "Câu hỏi làm hỏng hệ thống",
            "today": "2026-10-15",
            "category": "current",
            "expected_mode": "single",
            "expected_dates": ["2026-10-15"],
            "expected_provisions": [{"provision_key": "1/2099/QH99#D3.K1"}],
        },
    ],
}

CITATION = {
    "filename": "Khoản 1",
    "text": "1. Nội dung.",
    "chunk_id": "v1",
    "legal": {
        "provision_key": "1/2099/QH99#D3.K1",
        "number": "1/2099/QH99",
        "valid_from": "2024-08-01",
        "valid_to": None,
        "role": "primary",
    },
}


class FakeAnswerService:
    """Answers like the real use case, using the injected clock as 'today'."""

    def __init__(self, today) -> None:
        self.today = today
        self.seen_days: list[date] = []

    async def stream(self, question: str):
        day = self.today()
        self.seen_days.append(day)
        if "hỏng" in question:
            raise ConnectionError("qdrant down")
        if question.startswith("Năm 2025"):
            day = date(2025, 12, 31)
        temporal = TemporalQuery("single", (day,), "rule", "rule")
        yield LegalQAToken("Áp dụng tại ngày ... [1].")
        citations = [] if "xe máy" in question else [CITATION]
        yield LegalQAResult(temporal, citations, [])


class StubJudgeEvaluator(DeepEvalEvaluationService):
    """Scores DeepEval metrics without calling a judge model (no network in unit tests)."""

    def _run_deepeval_metric(self, metric, request):
        return self._metric_result(metric, 1.0, reason="stub judge")


def _run(tmp_path: Path, metrics):
    dataset_path = tmp_path / "golden.json"
    dataset_path.write_text(json.dumps(DATASET), encoding="utf-8")
    services: list[FakeAnswerService] = []

    def factory(today):
        service = FakeAnswerService(today)
        services.append(service)
        return service

    runner = LegalQAEvaluationRunner(answer_factory=factory, evaluator=StubJudgeEvaluator())
    config = LegalEvaluationRunConfig(
        dataset_path=str(dataset_path),
        output_dir=str(tmp_path / "reports"),
        metrics=metrics,
        run_name="legal",
    )
    report, paths = asyncio.run(runner.run(config))
    return report, paths, services


DETERMINISTIC = [
    EvaluationMetric.LEGAL_TEMPORAL_DATES,
    EvaluationMetric.LEGAL_TEMPORAL_CORRECTNESS,
    EvaluationMetric.LEGAL_CITATION_EXACTNESS,
]


def test_runner_pins_today_per_sample_and_scores(tmp_path: Path) -> None:
    report, paths, services = _run(tmp_path, DETERMINISTIC)
    assert len(services) == 1
    assert services[0].seen_days == [
        date(2026, 10, 15),
        date(2026, 1, 10),
        date(2026, 10, 15),
        date(2026, 10, 15),
    ]
    by_id = {result.sample_id: result for result in report.results}
    assert by_id["current-1"].passed
    assert by_id["past-1"].passed
    assert by_id["none-1"].passed
    assert [r.metric for r in by_id["none-1"].results] == [
        EvaluationMetric.LEGAL_TEMPORAL_DATES,
        EvaluationMetric.LEGAL_CITATION_EXACTNESS,
    ]
    assert not by_id["boom-1"].passed
    assert "qdrant down" in by_id["boom-1"].metadata["pipeline_error"]
    assert report.failed_evaluations == 1
    assert by_id["current-1"].metadata["category"] == "current"
    assert paths["json"].exists() and paths["markdown"].exists()


def test_context_dependent_metrics_are_dropped_without_contexts(tmp_path: Path) -> None:
    report, _, _ = _run(
        tmp_path, [EvaluationMetric.LEGAL_CITATION_EXACTNESS, EvaluationMetric.FAITHFULNESS]
    )
    by_id = {r.sample_id: r for r in report.results}
    assert [r.metric for r in by_id["none-1"].results] == [
        EvaluationMetric.LEGAL_CITATION_EXACTNESS
    ]
    assert EvaluationMetric.FAITHFULNESS in [r.metric for r in by_id["current-1"].results]


def test_max_samples_limits_the_run(tmp_path: Path) -> None:
    dataset_path = tmp_path / "golden.json"
    dataset_path.write_text(json.dumps(DATASET), encoding="utf-8")
    runner = LegalQAEvaluationRunner(
        answer_factory=FakeAnswerService, evaluator=DeepEvalEvaluationService()
    )
    config = LegalEvaluationRunConfig(
        dataset_path=str(dataset_path),
        output_dir=str(tmp_path / "reports"),
        metrics=DETERMINISTIC,
        max_samples=2,
    )
    report, _ = asyncio.run(runner.run(config))
    assert report.total_queries == 2


def test_only_sources_cited_in_the_answer_count(tmp_path: Path) -> None:
    class UncitedAnswer(FakeAnswerService):
        async def stream(self, question: str):
            async for event in super().stream(question):
                if isinstance(event, LegalQAToken):
                    yield LegalQAToken("Câu trả lời không trích dẫn nguồn nào.")
                else:
                    yield event

    dataset_path = tmp_path / "golden.json"
    dataset_path.write_text(
        json.dumps({**DATASET, "samples": DATASET["samples"][:1]}), encoding="utf-8"
    )
    runner = LegalQAEvaluationRunner(
        answer_factory=UncitedAnswer, evaluator=DeepEvalEvaluationService()
    )
    config = LegalEvaluationRunConfig(
        dataset_path=str(dataset_path),
        output_dir=str(tmp_path / "reports"),
        metrics=[EvaluationMetric.LEGAL_CITATION_EXACTNESS],
    )
    report, _ = asyncio.run(runner.run(config))
    [result] = report.results
    assert result.results[0].score == 0.0
    assert result.metadata["legal_actual"]["citations"] == []
    assert len(result.metadata["legal_actual"]["sources"]) == 1


def test_refusal_samples_skip_answer_relevancy(tmp_path: Path) -> None:
    report, _, _ = _run(
        tmp_path, [EvaluationMetric.ANSWER_RELEVANCY, EvaluationMetric.LEGAL_CITATION_EXACTNESS]
    )
    by_id = {r.sample_id: r for r in report.results}
    assert [r.metric for r in by_id["none-1"].results] == [
        EvaluationMetric.LEGAL_CITATION_EXACTNESS
    ]
