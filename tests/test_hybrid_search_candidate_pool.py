import pytest

from src.config.config import settings
from src.modules.retrieval.domain.services.hybrid_search import hybrid_search


class FakeBM25Index:
    def __init__(self):
        self.requested_k = None

    def search(self, query: str, k: int = 5) -> list[dict]:
        self.requested_k = k
        return [
            {
                "content": f"bm25 candidate {index}",
                "document_id": f"bm25-{index}",
                "chunk_index": index,
                "score": 1.0 - (index * 0.01),
            }
            for index in range(k)
        ]


class FakeRerankerLLM:
    async def chat_async(self, messages, temperature=0.1, max_tokens=256):
        return {"content": "[0, 1, 2, 3, 4]"}


class FakePortLLM:
    async def generate(self, messages, temperature=0.1, max_tokens=256):
        return "[1, 0]"


@pytest.mark.asyncio
async def test_hybrid_search_uses_candidate_pool_before_llm_reranking(monkeypatch):
    monkeypatch.setattr(settings, "reranking_mode", "llm")
    requested_dense_k = []

    def dense_search_fn(query_embedding, user_id=None, k=5):
        requested_dense_k.append(k)
        return [
            {
                "text": f"dense candidate {index}",
                "document_id": f"dense-{index}",
                "chunk_index": index,
                "score": 1.0 - (index * 0.01),
            }
            for index in range(k)
        ]

    bm25 = FakeBM25Index()
    results = await hybrid_search(
        query_embedding=[0.1],
        query_text="quy định xét tuyển sinh",
        user_id="user-1",
        bm25_index=bm25,
        k=5,
        llm_client=FakeRerankerLLM(),
        dense_search_fn=dense_search_fn,
    )

    assert requested_dense_k == [40]
    assert bm25.requested_k == 40
    assert len(results) == 5


@pytest.mark.asyncio
async def test_hybrid_search_requires_llm_adapter_in_llm_mode(monkeypatch):
    monkeypatch.setattr(settings, "reranking_mode", "llm")

    def dense_search_fn(query_embedding, user_id=None, k=5):
        return [
            {
                "text": f"dense candidate {index}",
                "document_id": f"dense-{index}",
                "chunk_index": index,
                "score": 1.0 - (index * 0.01),
            }
            for index in range(k)
        ]

    with pytest.raises(RuntimeError, match="LLM reranker is not configured"):
        await hybrid_search(
            query_embedding=[0.1],
            query_text="quy định xét tuyển sinh",
            user_id="user-1",
            bm25_index=None,
            k=5,
            dense_search_fn=dense_search_fn,
        )


@pytest.mark.asyncio
async def test_hybrid_search_llm_adapter_accepts_llm_port(monkeypatch):
    monkeypatch.setattr(settings, "reranking_mode", "llm")

    def dense_search_fn(query_embedding, user_id=None, k=5):
        return [
            {"text": "first", "document_id": "doc-1", "score": 0.9},
            {"text": "second", "document_id": "doc-2", "score": 0.8},
        ]

    results = await hybrid_search(
        query_embedding=[0.1],
        query_text="query",
        k=2,
        llm_client=FakePortLLM(),
        dense_search_fn=dense_search_fn,
    )

    assert [item["document_id"] for item in results] == ["doc-2", "doc-1"]
