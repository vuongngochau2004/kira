"""Unit tests for TEIEmbeddingAdapter (DUT AI BAAI/bge-m3)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from kira.config import EmbeddingProvider, settings
from kira.providers.embedding.factory import create_embedding_adapter
from kira.providers.embedding.tei import TEIEmbeddingAdapter


@pytest.fixture
def tei_adapter():
    return TEIEmbeddingAdapter(
        base_url="https://test-tei.example.com",
        api_key="test-key",
        model="BAAI/bge-m3",
        embedding_dim=1024,
    )


def test_tei_adapter_properties(tei_adapter):
    assert tei_adapter.dimension == 1024
    assert tei_adapter._base_url == "https://test-tei.example.com"
    assert tei_adapter._api_key == "test-key"
    assert tei_adapter._model == "BAAI/bge-m3"


@pytest.mark.asyncio
async def test_embed_single_text(tei_adapter):
    mock_vector = [0.1] * 1024
    resp = httpx.Response(200, json=[mock_vector])

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = resp

        vector = await tei_adapter.embed("Xin chào Việt Nam")

        assert len(vector) == 1024
        assert vector[0] == 0.1
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"] == {
            "inputs": ["Xin chào Việt Nam"],
            "normalize": True,
            "truncate": True,
        }
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_embed_batch_native(tei_adapter):
    mock_vectors = [[0.1] * 1024, [0.2] * 1024]
    resp = httpx.Response(200, json=mock_vectors)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = resp

        vectors = await tei_adapter.embed_batch(["Câu 1", "Câu 2"])

        assert len(vectors) == 2
        assert vectors[0][0] == 0.1
        assert vectors[1][0] == 0.2


@pytest.mark.asyncio
async def test_embed_batch_fallback_openai_compat(tei_adapter):
    mock_compat_response = {
        "data": [
            {"embedding": [0.3] * 1024, "index": 0},
            {"embedding": [0.4] * 1024, "index": 1},
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        req = httpx.Request("POST", "https://test-tei.example.com")
        resp1 = httpx.Response(404, json={"detail": "Not found"}, request=req)
        resp2 = httpx.Response(200, json=mock_compat_response, request=req)

        mock_post.side_effect = [resp1, resp2]

        vectors = await tei_adapter.embed_batch(["Câu 1", "Câu 2"])

        assert len(vectors) == 2
        assert vectors[0][0] == 0.3
        assert vectors[1][0] == 0.4
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_embed_batch_splits_into_configured_batch_size():
    adapter = TEIEmbeddingAdapter(base_url="https://test-tei.example.com", batch_size=8)
    texts = [f"Câu {i}" for i in range(20)]

    async def fake_post(url, json, headers):
        return httpx.Response(200, json=[[0.1] * 1024 for _ in json["inputs"]])

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = fake_post

        vectors = await adapter.embed_batch(texts)

    assert len(vectors) == 20
    assert [len(c.kwargs["json"]["inputs"]) for c in mock_post.call_args_list] == [8, 8, 4]


def test_tei_adapter_defaults_come_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "tei_embed_batch_size", 5)
    monkeypatch.setattr(settings, "tei_timeout_seconds", 77.0)

    adapter = TEIEmbeddingAdapter(base_url="https://test-tei.example.com")

    assert adapter._batch_size == 5
    assert adapter._timeout == 77.0


@pytest.mark.asyncio
async def test_embed_batch_timeout_does_not_fall_back(tei_adapter):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ReadTimeout("")

        with pytest.raises(httpx.ReadTimeout):
            await tei_adapter.embed_batch(["Câu 1"])

    assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_health_check_success(tei_adapter):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json={"status": "ok"})

        is_healthy = await tei_adapter.health_check()
        assert is_healthy is True


@pytest.mark.asyncio
async def test_health_check_failure(tei_adapter):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        is_healthy = await tei_adapter.health_check()
        assert is_healthy is False


@pytest.mark.asyncio
async def test_health_check_does_not_accept_generic_health_when_embedding_is_down(tei_adapter):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [
            httpx.Response(503),
            httpx.Response(200),
        ]

        assert await tei_adapter.health_check() is False

    assert mock_get.await_count == 1


def test_factory_creates_tei_adapter(monkeypatch):
    monkeypatch.setattr(settings, "embedding_provider", EmbeddingProvider.TEI)
    adapter = create_embedding_adapter()
    assert isinstance(adapter, TEIEmbeddingAdapter)
