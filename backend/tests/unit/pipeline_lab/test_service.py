"""Focused tests for the admin pipeline lab input boundary."""

from tempfile import SpooledTemporaryFile

import pytest
from fastapi import HTTPException, UploadFile

from kira.chat.intent.base import ClassificationResult, Intent
from kira.pipeline_lab import service
from kira.pipeline_lab.router import _read_document
from kira.pipeline_lab.schemas import RerankRequest
from kira.providers.ocr.paddle import OCRResult
from kira.retrieval.rerank.llm import (
    rerank_documents_with_llm,
)


@pytest.mark.asyncio
async def test_read_document_accepts_a_small_png() -> None:
    content = SpooledTemporaryFile()
    content.write(b"\x89PNG\r\n\x1a\ncontent")
    content.seek(0)
    file = UploadFile(filename="sample.png", file=content)

    suffix, content = await _read_document(file)

    assert suffix == "png"
    assert content.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_read_document_rejects_disguised_pdf() -> None:
    content = SpooledTemporaryFile()
    content.write(b"not a PDF")
    content.seek(0)
    file = UploadFile(filename="sample.pdf", file=content)

    with pytest.raises(HTTPException) as error:
        await _read_document(file)

    assert error.value.status_code == 400


def test_rerank_request_rejects_blank_candidates() -> None:
    with pytest.raises(ValueError):
        RerankRequest(query="search", documents=["  "])


@pytest.mark.asyncio
async def test_llm_reranks_when_top_k_includes_all_candidates() -> None:
    class FakeLLM:
        async def chat_async(self, **_: object) -> dict[str, str]:
            return {"content": "[1, 0]"}

    documents = [{"text": "first"}, {"text": "second"}]

    result = await rerank_documents_with_llm("query", documents, FakeLLM(), top_k=2)

    assert result == [documents[1], documents[0]]


@pytest.mark.asyncio
async def test_image_demo_returns_ocr_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeOCRClient:
        async def ocr_image_bytes(self, _: bytes) -> OCRResult:
            return OCRResult(text="read text", confidence=0.91, raw_response={"lines": []})

    monkeypatch.setattr(service, "get_ocr_client", lambda: FakeOCRClient())

    result = await service.inspect_document(b"image", "png")

    assert result["text"] == "read text"
    assert result["metadata"]["raw_response"] == {"lines": []}
    assert result["confidence"] == 0.91


@pytest.mark.asyncio
async def test_classifier_demo_uses_registered_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClassifier:
        async def classify(self, query: str, user_id: str) -> ClassificationResult:
            assert (query, user_id) == ("question", "user-1")
            return ClassificationResult(intent=Intent.RAG, confidence=0.8, reason="keyword")

    class FakeContainer:
        async def get(self, _: object) -> FakeClassifier:
            return FakeClassifier()

    async def fake_container() -> FakeContainer:
        return FakeContainer()

    monkeypatch.setattr(service, "get_container", fake_container)

    result = await service.inspect_classification("question", "user-1")

    assert result["intent"] == "rag"
    assert result["confidence"] == 0.8


@pytest.mark.asyncio
async def test_tei_demo_flags_service_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_rerank(
        query: str, candidates: list[dict[str, str]], top_k: int, timeout_seconds: float
    ) -> list[dict[str, str]]:
        assert query == "question"
        assert top_k == 2
        assert timeout_seconds > 0
        return candidates

    monkeypatch.setattr(service.settings, "reranking_mode", "tei")
    monkeypatch.setattr(service, "rerank_documents_with_tei", fake_rerank)

    result = await service.inspect_reranking("question", ["first", "second"], 2)

    assert result["fallback"] is True
    assert [item["id"] for item in result["results"]] == ["1", "2"]


@pytest.mark.asyncio
async def test_llm_demo_exposes_raw_ordering(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeLLM:
        async def chat_async(self, **_: object) -> dict[str, str]:
            return {"content": "[1, 0]"}

    monkeypatch.setattr(service.settings, "reranking_mode", "llm")
    monkeypatch.setattr(service, "get_llm_client", FakeLLM)

    result = await service.inspect_reranking("question", ["first", "second"], 2)

    assert [item["id"] for item in result["results"]] == ["2", "1"]
    assert result["raw_response"] == "[1, 0]"
