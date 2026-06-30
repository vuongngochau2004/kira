"""Unit tests for deterministic RAG evaluation metrics."""

import asyncio

from src.modules.evaluation.domain.models import (
    BatchEvaluationResponse,
    DEFAULT_METRICS,
    EvaluationMetric,
    EvaluationResponse,
    MetricResult,
)
from src.modules.evaluation.domain.models import EvaluationRequest
from src.modules.evaluation.domain.service import DeepEvalEvaluationService
from src.modules.evaluation.metrics import hit_rate_at_k, mean_reciprocal_rank, recall_at_k
from src.modules.evaluation.reports.reporter import EvaluationReporter
from src.modules.evaluation.runners.rag_pipeline_runner import RAGPipelineEvaluationRunner


def test_default_metrics_cover_actionable_rag_diagnostics() -> None:
    """Default benchmarks retain one metric for each actionable RAG failure mode."""
    assert DEFAULT_METRICS == [
        EvaluationMetric.ANSWER_RELEVANCY,
        EvaluationMetric.FAITHFULNESS,
        EvaluationMetric.CONTEXTUAL_RECALL,
    ]


def test_retrieval_metrics_respect_rank_and_top_k() -> None:
    """Hit, MRR, and recall use expected context IDs with ranking semantics."""
    expected = ["document-a:1", "document-b:2"]
    retrieved = ["document-x:0", "document-b:2", "document-a:1"]

    assert hit_rate_at_k(expected, retrieved, k=1)[0] == 0.0
    assert hit_rate_at_k(expected, retrieved, k=2)[0] == 1.0
    assert mean_reciprocal_rank(expected, retrieved)[0] == 0.5
    assert recall_at_k(expected, retrieved, k=2)[0] == 0.5
    assert recall_at_k(expected, retrieved, k=3)[0] == 1.0


def test_retrieval_metrics_are_skipped_without_expected_context_ids() -> None:
    """No-answer and unlabeled samples do not distort retrieval aggregates."""
    request = EvaluationRequest(query="q", answer="a")

    assert DeepEvalEvaluationService._should_skip_metric(EvaluationMetric.HIT_RATE_AT_K, request)


def test_retrieved_context_ids_preserve_document_ranking() -> None:
    """One retrieved document maps to one ID, so ranking metrics are not diluted."""
    chunked = type("Document", (), {"doc_id": "document-a", "chunk_index": 2})()
    unchunked = type("Document", (), {"doc_id": "document-b", "chunk_index": None})()

    assert RAGPipelineEvaluationRunner._retrieved_context_ids([chunked, unchunked]) == [
        "document-a:2",
        "document-b",
    ]


def test_service_adds_deterministic_retrieval_scores() -> None:
    """The evaluation service returns retrieval metrics without an LLM judge."""
    request = EvaluationRequest(
        query="q",
        answer="a",
        metrics=[
            EvaluationMetric.HIT_RATE_AT_K,
            EvaluationMetric.MRR,
            EvaluationMetric.RECALL_AT_K,
        ],
        retrieval_k=2,
        metadata={
            "expected_context_ids": ["document-a:1", "document-b:2"],
            "retrieved_context_ids": ["document-x:0", "document-a:1", "document-b:2"],
        },
    )

    response = asyncio.run(DeepEvalEvaluationService().evaluate(request))

    assert {result.metric for result in response.results} == set(request.metrics)
    assert [result.score for result in response.results] == [1.0, 0.5, 0.5]


def test_retrieval_metrics_prioritize_ids_over_generation_contexts() -> None:
    """Compressed generation context must not make deterministic retrieval look failed."""
    request = EvaluationRequest(
        query="q",
        answer="a",
        contexts=["raw expected evidence text"],
        generation_contexts=["compressed text that no longer contains the full evidence"],
        reference_contexts=["raw expected evidence text"],
        metrics=[EvaluationMetric.MRR, EvaluationMetric.RECALL_AT_K],
        retrieval_k=5,
        metadata={
            "expected_context_ids": ["document-a:1"],
            "retrieved_context_ids": ["document-a:1"],
        },
    )

    response = asyncio.run(DeepEvalEvaluationService().evaluate(request))

    assert [result.score for result in response.results] == [1.0, 1.0]


def test_report_includes_actionable_guidance_for_aggregated_metrics() -> None:
    """Reports map low aggregate scores to the component that needs tuning."""
    report = BatchEvaluationResponse(
        batch_id="batch",
        total_queries=1,
        successful_evaluations=1,
        failed_evaluations=0,
        results=[],
        aggregated_scores={"mrr": 0.4, "faithfulness": 0.6},
        started_at="2026-06-24T00:00:00",
        completed_at="2026-06-24T00:00:01",
        total_duration_seconds=1.0,
    )

    markdown = EvaluationReporter()._to_markdown(report)

    assert "## Improvement Guide" in markdown
    assert "hybrid-search weights" in markdown
    assert "grounding instructions" in markdown


def test_evaluation_service_classifies_generation_failure_after_good_retrieval() -> None:
    """Good retrieval plus low answer relevancy is reported as generation failure."""
    analysis = DeepEvalEvaluationService._failure_analysis(
        [
            MetricResult(
                metric=EvaluationMetric.MRR,
                score=1.0,
                threshold=0.7,
                passed=True,
            ),
            MetricResult(
                metric=EvaluationMetric.RECALL_AT_K,
                score=1.0,
                threshold=0.7,
                passed=True,
            ),
            MetricResult(
                metric=EvaluationMetric.ANSWER_RELEVANCY,
                score=0.2,
                threshold=0.7,
                passed=False,
            ),
        ]
    )

    assert analysis["primary_category"] == "generation_answer"
    assert analysis["retrieval_failed"] is False
    assert analysis["generation_failed"] is True


def test_report_includes_failure_analysis_section() -> None:
    """Markdown reports separate retrieval and generation failure classes."""
    report = BatchEvaluationResponse(
        batch_id="batch",
        total_queries=1,
        successful_evaluations=1,
        failed_evaluations=0,
        results=[
            EvaluationResponse(
                evaluation_id="eval-1",
                sample_id="sample-1",
                query="q",
                answer="a",
                results=[],
                overall_score=0.4,
                passed=False,
                metadata={
                    "failure_analysis": {
                        "categories": ["generation_answer"],
                        "retrieval_failed": False,
                        "generation_failed": True,
                    }
                },
            )
        ],
        aggregated_scores={"answer_relevancy": 0.2},
        started_at="2026-06-24T00:00:00",
        completed_at="2026-06-24T00:00:01",
        total_duration_seconds=1.0,
    )

    markdown = EvaluationReporter()._to_markdown(report)

    assert "## Failure Analysis" in markdown
    assert "Generation failures: 1" in markdown
    assert "| generation_answer | 1 | sample-1 |" in markdown


def test_is_semantic_match() -> None:
    """is_semantic_match correctly matches identical, substring, and high token overlap contexts."""
    from src.modules.evaluation.metrics.custom import is_semantic_match

    # Substring check
    assert is_semantic_match("Đây là nội dung văn bản tìm kiếm", "văn bản tìm kiếm") is True
    assert is_semantic_match("văn bản tìm kiếm", "Đây là nội dung văn bản tìm kiếm") is True

    # High overlap check (threshold 0.65)
    assert (
        is_semantic_match(
            "quy định về thời gian thử việc tối đa là hai tháng theo quy chế công ty",
            "quy định về thời gian thử việc tối đa là 2 tháng",
        )
        is True
    )

    # Low overlap check
    assert (
        is_semantic_match(
            "quy trình tuyển dụng nhân sự năm nay",
            "quy định về thời gian thử việc tối đa là 2 tháng",
        )
        is False
    )


def test_retrieval_metrics_content_based() -> None:
    """hit_rate, MRR, and recall content-based versions correctly match expected texts using semantic matching."""
    from src.modules.evaluation.metrics.custom import (
        hit_rate_at_k_text,
        mean_reciprocal_rank_text,
        recall_at_k_text,
    )

    expected_texts = [
        "quy định về thời gian thử việc tối đa là 2 tháng",
        "lương thử việc bằng 85% lương chính thức",
    ]
    retrieved_texts = [
        "quy trình xin nghỉ phép năm",
        "quy định về thời gian thử việc tối đa là hai tháng theo quy chế",  # matches first expected
        "hồ sơ cần nộp khi nhận việc",
    ]

    # k=1 (only "quy trình xin nghỉ phép năm" -> no match)
    assert hit_rate_at_k_text(expected_texts, retrieved_texts, k=1)[0] == 0.0
    # k=2 (first two retrieved -> matches first expected)
    assert hit_rate_at_k_text(expected_texts, retrieved_texts, k=2)[0] == 1.0
    # MRR (first match is rank 2)
    assert mean_reciprocal_rank_text(expected_texts, retrieved_texts)[0] == 0.5
    # Recall @ 2 (matches 1 out of 2 expected)
    assert recall_at_k_text(expected_texts, retrieved_texts, k=2)[0] == 0.5
    # Recall @ 3 (matches 1 out of 2 expected)
    assert recall_at_k_text(expected_texts, retrieved_texts, k=3)[0] == 0.5


def test_refusal_correctness_heuristic() -> None:
    """refusal_correctness correctly uses fast heuristic matching."""
    from src.modules.evaluation.metrics.custom import refusal_correctness

    # should refuse and answers with refusal marker
    score, reason = asyncio.run(
        refusal_correctness("Tôi không tìm thấy thông tin này", should_refuse=True)
    )
    assert score == 1.0
    assert "heuristic" in reason

    # should not refuse and answers normally
    score, reason = asyncio.run(refusal_correctness("Thử việc tối đa 2 tháng", should_refuse=False))
    assert score == 1.0
    assert "heuristic" in reason

    # should refuse but answers normally -> score 0
    score, reason = asyncio.run(refusal_correctness("Thử việc tối đa 2 tháng", should_refuse=True))
    assert score == 0.0
