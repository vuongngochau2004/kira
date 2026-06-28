import pytest

from src.modules.retrieval.domain.services.hybrid_search import hybrid_search, set_llm_client


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


@pytest.mark.asyncio
async def test_hybrid_search_uses_candidate_pool_before_llm_reranking(monkeypatch):
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
    set_llm_client(FakeRerankerLLM())

    try:
        results = await hybrid_search(
            query_embedding=[0.1],
            query_text="quy định xét tuyển sinh",
            user_id="user-1",
            bm25_index=bm25,
            k=5,
            enable_rerank=True,
            dense_search_fn=dense_search_fn,
        )
    finally:
        set_llm_client(None)

    assert requested_dense_k == [40]
    assert bm25.requested_k == 40
    assert len(results) == 5


@pytest.mark.asyncio
async def test_hybrid_search_keeps_final_k_when_reranking_has_no_llm():
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

    set_llm_client(None)

    results = await hybrid_search(
        query_embedding=[0.1],
        query_text="quy định xét tuyển sinh",
        user_id="user-1",
        bm25_index=None,
        k=5,
        enable_rerank=True,
        dense_search_fn=dense_search_fn,
    )

    assert len(results) == 5
