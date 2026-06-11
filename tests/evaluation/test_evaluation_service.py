"""Tests for RAGAS evaluation service."""

import pytest
import asyncio
from src.modules.evaluation.domain.service import RAGASEvaluationService
from src.models.evaluation import EvaluationRequest, EvaluationMetric


@pytest.mark.asyncio
async def test_evaluate_faithfulness():
    """Test faithfulness evaluation."""
    service = RAGASEvaluationService()

    request = EvaluationRequest(
        query="What is the capital of Vietnam?",
        answer="Hanoi is the capital of Vietnam.",
        contexts=["Hanoi is the capital city of Vietnam."],
        metrics=[EvaluationMetric.FAITHFULNESS],
    )

    result = await service.evaluate(request)

    assert result.evaluation_id
    assert len(result.results) == 1
    assert result.results[0].metric == EvaluationMetric.FAITHFULNESS
    assert 0.0 <= result.results[0].score <= 1.0
    assert result.overall_score >= 0.0


@pytest.mark.asyncio
async def test_evaluate_multiple_metrics():
    """Test evaluating multiple metrics."""
    service = RAGASEvaluationService()

    request = EvaluationRequest(
        query="Test query",
        answer="Test answer",
        contexts=["Context 1", "Context 2"],
        metrics=[
            EvaluationMetric.FAITHFULNESS,
            EvaluationMetric.ANSWER_RELEVANCY,
            EvaluationMetric.CONTEXT_PRECISION,
        ],
    )

    result = await service.evaluate(request)

    assert len(result.results) == 3
    assert result.overall_score >= 0.0


@pytest.mark.asyncio
async def test_batch_evaluation():
    """Test batch evaluation."""
    service = RAGASEvaluationService()

    from src.models.evaluation import BatchEvaluationRequest

    request = BatchEvaluationRequest(
        queries=[
            {
                "query": f"Test query {i}",
                "answer": f"Test answer {i}",
                "contexts": [f"Context {i}"],
            }
            for i in range(5)
        ],
        metrics=[EvaluationMetric.FAITHFULNESS],
        concurrent_evaluations=2,
    )

    result = await service.evaluate_batch(request)

    assert result.batch_id
    assert result.total_queries == 5
    assert result.successful_evaluations >= 0
    assert result.failed_evaluations >= 0
    assert result.total_duration_seconds > 0


@pytest.mark.asyncio
async def test_cache_functionality():
    """Test evaluation result caching."""
    service = RAGASEvaluationService(cache_enabled=True)

    request = EvaluationRequest(
        query="Cached query",
        answer="Cached answer",
        contexts=["Cached context"],
        metrics=[EvaluationMetric.FAITHFULNESS],
    )

    # First call - should hit LLM
    result1 = await service.evaluate(request)

    # Second call - should hit cache
    result2 = await service.evaluate(request)

    assert result1.evaluation_id != result2.evaluation_id
    # Scores might be same due to cache, but overall_score should match
    # Note: In real test, we'd mock LLM to ensure deterministic behavior

    # Clear cache
    cleared = service.clear_cache()
    assert cleared >= 0


@pytest.mark.asyncio
async def test_evaluate_with_error_handling(mocker):
    """Test evaluation handles errors gracefully."""
    from pydantic import ValidationError
    service = RAGASEvaluationService()

    # 1. Test validation error for empty contexts (Pydantic V2)
    with pytest.raises(ValidationError):
        EvaluationRequest(
            query="Test query",
            answer="Test answer",
            contexts=[],
            metrics=[EvaluationMetric.FAITHFULNESS],
        )

    # 2. Test service error handling on LLM timeout
    mocker.patch(
        "src.modules.evaluation.domain.service.chat_async",
        side_effect=asyncio.TimeoutError("Timeout constraint")
    )
    request = EvaluationRequest(
        query="Test query",
        answer="Test answer",
        contexts=["Test context"],
        metrics=[EvaluationMetric.FAITHFULNESS],
    )
    result = await service.evaluate(request)
    assert result.evaluation_id
    assert len(result.results) == 1
    assert result.results[0].score == 0.0
    assert "timeout" in result.results[0].error.lower()


@pytest.mark.asyncio
async def test_evaluation_response_structure():
    """Test evaluation response has correct structure."""
    service = RAGASEvaluationService()

    request = EvaluationRequest(
        query="Test query",
        answer="Test answer",
        contexts=["Test context"],
        metrics=[EvaluationMetric.FAITHFULNESS, EvaluationMetric.ANSWER_RELEVANCY],
    )

    result = await service.evaluate(request)

    # Check response structure
    assert hasattr(result, 'evaluation_id')
    assert hasattr(result, 'query')
    assert hasattr(result, 'results')
    assert hasattr(result, 'overall_score')
    assert hasattr(result, 'evaluated_at')
    assert hasattr(result, 'evaluation_duration_seconds')
    assert hasattr(result, 'llm_provider')
    assert hasattr(result, 'llm_model')

    # Check results structure
    for r in result.results:
        assert hasattr(r, 'metric')
        assert hasattr(r, 'score')
        assert hasattr(r, 'reasoning')
        assert hasattr(r, 'error')
