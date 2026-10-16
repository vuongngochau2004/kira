from datetime import date

import pytest

from src.modules.legal.infrastructure.reranker import ConfiguredLegalReranker
from tests.legal_fakes import make_hit

HITS = [make_hit(f"31/2024/QH15#D{i}", f"văn bản {i}", date(2024, 8, 1)) for i in range(1, 4)]


async def test_disabled_keeps_order() -> None:
    reranker = ConfiguredLegalReranker(enabled=False, mode="tei", llm_client_provider=lambda: None)
    assert await reranker.rerank("q", HITS, 2) == HITS[:2]


async def test_tei_mode_reorders(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_tei(query, candidates, top_k=5, **kwargs):
        return list(reversed(candidates))[:top_k]

    monkeypatch.setattr(
        "src.modules.retrieval.domain.services.reranking.tei_reranker.rerank_documents_with_tei",
        fake_tei,
    )
    reranker = ConfiguredLegalReranker(enabled=True, mode="tei", llm_client_provider=lambda: None)
    assert await reranker.rerank("q", HITS, 2) == [HITS[2], HITS[1]]


async def test_llm_mode_without_client_keeps_order() -> None:
    reranker = ConfiguredLegalReranker(enabled=True, mode="llm", llm_client_provider=lambda: None)
    assert await reranker.rerank("q", HITS, 3) == HITS


async def test_llm_mode_uses_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client = object()

    async def fake_llm(query, candidates, llm_client, top_k=5, **kwargs):
        assert llm_client is client
        return [candidates[1], candidates[0]]

    monkeypatch.setattr(
        "src.modules.legal.infrastructure.reranker.rerank_documents_with_llm", fake_llm
    )
    reranker = ConfiguredLegalReranker(enabled=True, mode="llm", llm_client_provider=lambda: client)
    assert await reranker.rerank("q", HITS, 2) == [HITS[1], HITS[0]]


async def test_reranker_failure_keeps_order(monkeypatch: pytest.MonkeyPatch) -> None:
    async def broken(*args, **kwargs):
        raise TimeoutError("slow")

    monkeypatch.setattr(
        "src.modules.legal.infrastructure.reranker.rerank_documents_with_llm", broken
    )
    reranker = ConfiguredLegalReranker(enabled=True, mode="llm", llm_client_provider=object)
    assert await reranker.rerank("q", HITS, 2) == HITS[:2]
