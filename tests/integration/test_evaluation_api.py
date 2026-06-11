"""Integration tests for evaluation API."""

import pytest
from httpx import AsyncClient
from src.models.evaluation import EvaluationRequest, EvaluationMetric


@pytest.mark.asyncio
async def test_evaluate_endpoint(authenticated_client: AsyncClient):
    """Test /api/v1/evaluation/evaluate endpoint."""
    response = await authenticated_client.post(
        "/api/v1/evaluation/evaluate",
        json={
            "query": "Test question",
            "answer": "Test answer",
            "contexts": ["Test context"],
            "metrics": ["faithfulness"],
        },
    )

    # Note: This will return 503 if RAGAS evaluation is disabled
    assert response.status_code in [200, 503]

    if response.status_code == 200:
        data = response.json()
        assert "evaluation_id" in data
        assert "results" in data
        assert data["overall_score"] >= 0.0


@pytest.mark.asyncio
async def test_batch_evaluate_endpoint(authenticated_client: AsyncClient):
    """Test /api/v1/evaluation/evaluate/batch endpoint."""
    response = await authenticated_client.post(
        "/api/v1/evaluation/evaluate/batch",
        json={
            "queries": [
                {
                    "query": f"Question {i}",
                    "answer": f"Answer {i}",
                    "contexts": [f"Context {i}"],
                }
                for i in range(3)
            ],
            "metrics": ["faithfulness"],
            "concurrent_evaluations": 2,
        },
    )

    # Note: This will return 503 if RAGAS evaluation is disabled
    assert response.status_code in [200, 503]

    if response.status_code == 200:
        data = response.json()
        assert data["total_queries"] == 3
        assert "aggregated_scores" in data


@pytest.mark.asyncio
async def test_golden_dataset_crud(authenticated_client: AsyncClient):
    """Test golden dataset CRUD operations."""
    # Create dataset
    create_response = await authenticated_client.post(
        "/api/v1/evaluation/evaluate/datasets",
        json={
            "dataset_id": "test-dataset",
            "name": "Test Dataset",
            "samples": [
                {
                    "query": "Test",
                    "answer": "Answer",
                    "contexts": ["Context"],
                }
            ],
        },
    )
    assert create_response.status_code == 201

    # List datasets
    list_response = await authenticated_client.get("/api/v1/evaluation/evaluate/datasets")
    assert list_response.status_code == 200
    datasets = list_response.json()
    assert len(datasets) > 0


@pytest.mark.asyncio
async def test_clear_cache_endpoint(authenticated_client: AsyncClient):
    """Test /api/v1/evaluation/cache endpoint."""
    response = await authenticated_client.delete("/api/v1/evaluation/evaluate/cache")
    assert response.status_code == 200
    data = response.json()
    assert "cleared_entries" in data


@pytest.mark.asyncio
async def test_real_time_evaluation_in_chat(authenticated_client: AsyncClient):
    """Test real-time evaluation in chat SSE stream."""
    # Note: This test requires SSE client and streaming response handling
    # For now, we just test the endpoint accepts the parameters
    response = await authenticated_client.post(
        "/api/v1/chat/stream",
        json={
            "message": "Test question",
            "evaluate": True,
            "evaluation_metrics": ["faithfulness", "answer_relevancy"],
        },
    )

    # Should return 200 with streaming response
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_evaluate_dataset_endpoint(authenticated_client: AsyncClient):
    """Test evaluating a golden dataset."""
    # First, check if example dataset exists
    list_response = await authenticated_client.get("/api/v1/evaluation/evaluate/datasets")
    assert list_response.status_code == 200
    datasets = list_response.json()

    if datasets:
        # Try to evaluate first dataset
        dataset_id = datasets[0]["dataset_id"]
        response = await authenticated_client.get(
            f"/api/v1/evaluation/evaluate/datasets/{dataset_id}/evaluate"
        )

        # Note: This will return 503 if RAGAS evaluation is disabled
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "batch_id" in data
            assert "total_queries" in data
