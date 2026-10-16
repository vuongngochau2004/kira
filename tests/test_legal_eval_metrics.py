import asyncio
from datetime import date

import pytest

from src.modules.evaluation.domain.models import (
    DEFAULT_LEGAL_METRICS,
    EvaluationMetric,
    EvaluationRequest,
    MetricResult,
)
from src.modules.evaluation.domain.service import DeepEvalEvaluationService
from src.modules.evaluation.metrics import (
    citation_exactness,
    cited_sources,
    temporal_correctness,
    temporal_date_accuracy,
)

D1, D2 = date(2026, 6, 30), date(2026, 7, 1)


def _citation(key: str, valid_from: str, valid_to: str | None, role: str = "primary") -> dict:
    return {
        "filename": key,
        "text": "nội dung",
        "chunk_id": f"{key}@{valid_from}",
        "legal": {
            "provision_key": key,
            "number": key.split("#")[0],
            "valid_from": valid_from,
            "valid_to": valid_to,
            "role": role,
        },
    }


OLD = _citation("1/2099/QH99#D3.K1", "2024-08-01", "2026-07-01")
NEW = _citation("1/2099/QH99#D3.K1", "2026-07-01", None)


def test_temporal_date_accuracy() -> None:
    assert temporal_date_accuracy("single", [D2], "single", [D2])[0] == 1.0
    assert temporal_date_accuracy("single", [D2], "single", [D1])[0] == 0.0
    assert temporal_date_accuracy("compare", [D1, D2], "single", [D2])[0] == 0.0
    assert temporal_date_accuracy("compare", [D1, D2], "compare", [D1, date(2026, 8, 1)])[0] == 0.5


def test_temporal_correctness_single_date() -> None:
    assert temporal_correctness("single", [date(2025, 12, 31)], [OLD])[0] == 1.0
    score, reason = temporal_correctness("single", [date(2025, 12, 31)], [OLD, NEW])
    assert score == 0.5
    assert "1/2099/QH99#D3.K1" in reason


def test_temporal_correctness_compare_checks_each_side_at_its_date() -> None:
    before = _citation("1/2099/QH99#D3.K1", "2024-08-01", "2026-07-01", role="before")
    after = _citation("1/2099/QH99#D3.K1", "2026-07-01", None, role="after")
    assert temporal_correctness("compare", [D1, D2], [before, after])[0] == 1.0
    swapped = [dict(before, legal={**before["legal"], "role": "after"})]
    assert temporal_correctness("compare", [D1, D2], swapped)[0] == 0.0
    unchanged = _citation("1/2099/QH99#D4", "2024-08-01", None, role="primary")
    assert temporal_correctness("compare", [D1, D2], [unchanged])[0] == 1.0


def test_citation_exactness() -> None:
    expected = [{"provision_key": "1/2099/QH99#D3.K1", "valid_from": date(2026, 7, 1)}]
    assert citation_exactness(expected, [NEW])[0] == 1.0
    assert citation_exactness(expected, [OLD])[0] == 0.0
    any_version = [{"provision_key": "1/2099/QH99#D3.K1", "valid_from": None}]
    assert citation_exactness(any_version, [OLD])[0] == 1.0
    two = expected + [{"provision_key": "1/2099/QH99#D4", "valid_from": None}]
    score, reason = citation_exactness(two, [NEW, _citation("9/2099/QH99#D1", "2024-01-01", None)])
    assert score == 0.5
    assert "precision 0.50" in reason


def test_no_answer_scores_by_absence_of_citations() -> None:
    assert citation_exactness([], [])[0] == 1.0
    assert citation_exactness([], [NEW])[0] == 0.0


def _request(metrics, expected=None, actual=None) -> EvaluationRequest:
    metadata = {}
    if expected is not None:
        metadata["legal_expected"] = expected
    if actual is not None:
        metadata["legal_actual"] = actual
    return EvaluationRequest(query="q", answer="a", metrics=metrics, metadata=metadata)


def test_service_scores_legal_metrics_from_metadata() -> None:
    request = _request(
        [
            EvaluationMetric.LEGAL_TEMPORAL_DATES,
            EvaluationMetric.LEGAL_TEMPORAL_CORRECTNESS,
            EvaluationMetric.LEGAL_CITATION_EXACTNESS,
        ],
        expected={
            "mode": "single",
            "dates": ["2026-10-15"],
            "provisions": [{"provision_key": "1/2099/QH99#D3.K1", "valid_from": "2026-07-01"}],
        },
        actual={"mode": "single", "dates": ["2026-10-15"], "citations": [NEW]},
    )
    response = asyncio.run(DeepEvalEvaluationService().evaluate(request))
    assert [(r.metric, r.score) for r in response.results] == [
        (EvaluationMetric.LEGAL_TEMPORAL_DATES, 1.0),
        (EvaluationMetric.LEGAL_TEMPORAL_CORRECTNESS, 1.0),
        (EvaluationMetric.LEGAL_CITATION_EXACTNESS, 1.0),
    ]
    assert response.passed


def test_legal_metrics_are_skipped_without_legal_metadata() -> None:
    request = _request(
        [EvaluationMetric.LEGAL_CITATION_EXACTNESS, EvaluationMetric.CITATION_ACCURACY]
    )
    response = asyncio.run(DeepEvalEvaluationService().evaluate(request))
    assert [r.metric for r in response.results] == [EvaluationMetric.CITATION_ACCURACY]


def test_temporal_correctness_is_skipped_when_nothing_is_cited() -> None:
    request = _request(
        [EvaluationMetric.LEGAL_TEMPORAL_CORRECTNESS],
        expected={"mode": "single", "dates": ["2026-10-15"], "provisions": []},
        actual={"mode": "single", "dates": ["2026-10-15"], "citations": []},
    )
    assert asyncio.run(DeepEvalEvaluationService().evaluate(request)).results == []


@pytest.mark.parametrize("metric", DEFAULT_LEGAL_METRICS)
def test_default_legal_metrics_are_valid(metric: EvaluationMetric) -> None:
    assert metric.canonical == metric


def test_cited_sources_follow_answer_markers() -> None:
    a, b, c, d = ({"n": i} for i in range(4))
    answer = "Theo [2] và [1, 3]. Nhắc lại [2]; [9] không tồn tại."
    assert cited_sources(answer, [a, b, c, d]) == [b, a, c]
    assert cited_sources("Không có trích dẫn.", [a, b]) == []


def test_citation_flood_is_not_rewarded() -> None:
    expected = [{"provision_key": "1/2099/QH99#D3.K1", "valid_from": None}]
    noise = [_citation(f"9/2099/QH99#D{i}", "2024-01-01", None) for i in range(10)]
    score, reason = citation_exactness(expected, [NEW, *noise])
    assert score < 0.2
    assert "recall 1.00" in reason


def test_temporal_correctness_is_judged_at_the_expected_date() -> None:
    request = _request(
        [EvaluationMetric.LEGAL_TEMPORAL_CORRECTNESS],
        expected={"mode": "single", "dates": ["2020-06-01"], "provisions": []},
        actual={"mode": "single", "dates": ["2026-10-16"], "citations": [NEW]},
    )
    [result] = asyncio.run(DeepEvalEvaluationService().evaluate(request)).results
    assert result.score == 0.0


def test_failure_analysis_names_legal_failures() -> None:
    def failed(metric: EvaluationMetric) -> MetricResult:
        return MetricResult(metric=metric, score=0.0, threshold=0.7, passed=False)

    analysis = DeepEvalEvaluationService._failure_analysis(
        [
            failed(EvaluationMetric.LEGAL_TEMPORAL_DATES),
            failed(EvaluationMetric.LEGAL_TEMPORAL_CORRECTNESS),
            failed(EvaluationMetric.LEGAL_CITATION_EXACTNESS),
        ]
    )
    assert analysis["categories"] == [
        "legal_temporal_resolution",
        "legal_version_selection",
        "legal_citation",
    ]


def test_default_legal_metrics_check_refusals() -> None:
    assert EvaluationMetric.REFUSAL_CORRECTNESS in DEFAULT_LEGAL_METRICS
