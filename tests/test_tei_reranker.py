"""Unit tests for TEI Cross-Encoder Reranker."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.config.config import settings
from src.modules.retrieval.domain.services.hybrid_search import hybrid_search
from src.modules.retrieval.domain.services.reranking.tei_reranker import (
    extract_document_text,
    health_check_tei_reranker,
    rerank_documents_with_tei,
)


def test_extract_document_text():
    assert extract_document_text({"text": "Hello text"}) == "Hello text"
    assert extract_document_text({"content": "Hello content"}) == "Hello content"
    assert extract_document_text({"metadata": {"text": "Hello metadata"}}) == "Hello metadata"
    assert extract_document_text({}) == ""


@pytest.mark.asyncio
async def test_rerank_documents_with_tei_success():
    candidates = [
        {"id": "doc0", "text": "Hà Nội là thủ đô của Việt Nam."},
        {"id": "doc1", "text": "Đà Nẵng là thành phố đáng sống."},
        {"id": "doc2", "text": "TP Hồ Chí Minh rất sôi động."},
    ]

    mock_tei_response = [
        {"index": 1, "score": 0.95},
        {"index": 0, "score": 0.60},
        {"index": 2, "score": 0.10},
    ]

    req = httpx.Request("POST", "https://test-tei.example.com/rerank")
    resp = httpx.Response(200, json=mock_tei_response, request=req)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = resp

        reranked = await rerank_documents_with_tei(
            query="Thành phố Đà Nẵng",
            candidates=candidates,
            top_k=2,
            base_url="https://test-tei.example.com",
            api_key="test-key",
            min_score_threshold=0.2,
        )

        assert len(reranked) == 2
        assert reranked[0]["id"] == "doc1"
        assert reranked[0]["rerank_score"] == 0.95
        assert reranked[1]["id"] == "doc0"
        assert reranked[1]["rerank_score"] == 0.60

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["query"] == "Thành phố Đà Nẵng"
        assert len(call_kwargs["json"]["texts"]) == 3
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_rerank_documents_with_tei_fallback_on_error():
    candidates = [
        {"id": "doc0", "text": "Văn bản 1"},
        {"id": "doc1", "text": "Văn bản 2"},
    ]

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        reranked = await rerank_documents_with_tei(
            query="Tìm kiếm",
            candidates=candidates,
            top_k=2,
        )

        # On error, fallback to original order
        assert len(reranked) == 2
        assert reranked[0]["id"] == "doc0"
        assert reranked[1]["id"] == "doc1"


@pytest.mark.asyncio
async def test_health_check_tei_reranker():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json={"status": "ok"})

        assert await health_check_tei_reranker("https://test.com") is True

        mock_get.side_effect = httpx.HTTPError("error")
        assert await health_check_tei_reranker("https://test.com") is False


@pytest.mark.asyncio
async def test_hybrid_search_uses_tei_reranker(monkeypatch):
    monkeypatch.setattr(settings, "reranking_enabled", True)
    monkeypatch.setattr(settings, "reranking_mode", "tei")

    dense_candidates = [
        {"id": "docA", "text": "Nội dung A", "score": 0.8},
        {"id": "docB", "text": "Nội dung B", "score": 0.7},
    ]

    async def mock_dense_search(**kwargs):
        return dense_candidates

    with patch(
        "src.modules.retrieval.domain.services.reranking.tei_reranker.rerank_documents_with_tei",
        new_callable=AsyncMock,
    ) as mock_tei:
        mock_tei.return_value = [
            {"id": "docB", "text": "Nội dung B", "rerank_score": 0.99},
            {"id": "docA", "text": "Nội dung A", "rerank_score": 0.50},
        ]

        results = await hybrid_search(
            query_embedding=[0.1] * 1024,
            query_text="query",
            dense_search_fn=mock_dense_search,
            enable_rerank=True,
            k=2,
        )

        assert len(results) == 2
        assert results[0]["id"] == "docB"
        assert results[0]["rerank_score"] == 0.99
        mock_tei.assert_called_once()
