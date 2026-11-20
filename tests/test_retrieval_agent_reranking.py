import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

os.environ.setdefault("DEBUG", "false")

from src.modules.rag.orchestration.agents.retrieval_agent import RetrievalAgent
from src.modules.rag.orchestration.state.rag_state import DocumentWithScore, RetrievalAgentConfig


class FakeLLM:
    async def generate(self, messages, temperature=0.7, max_tokens=2000, **kwargs):
        return """
        {
          "rankings": [
            {"index": 2, "score": 0.93, "reason": "direct match"},
            {"index": 0, "score": 0.81, "reason": "partial match"}
          ]
        }
        """


def _docs():
    return [
        DocumentWithScore(
            doc_id=uuid4(),
            content="quy định xét tuyển sinh đại học",
            filename="doc-1.pdf",
            page_number=1,
            chunk_index=0,
            score=0.02,
        ),
        DocumentWithScore(
            doc_id=uuid4(),
            content="thông báo trúng tuyển và nhập học",
            filename="doc-2.pdf",
            page_number=2,
            chunk_index=1,
            score=0.01,
        ),
        DocumentWithScore(
            doc_id=uuid4(),
            content="điều kiện đăng ký xét tuyển và phương thức xét tuyển",
            filename="doc-3.pdf",
            page_number=3,
            chunk_index=2,
            score=0.005,
        ),
    ]


@pytest.mark.asyncio
async def test_llm_reranking_uses_structured_output():
    config = RetrievalAgentConfig(reranker_model="llm", rerank_top_k=2)
    agent = RetrievalAgent(config=config, llm_client=FakeLLM())

    reranked = await agent._rerank_documents("quy định xét tuyển sinh", _docs())

    assert [doc.filename for doc in reranked] == ["doc-3.pdf", "doc-1.pdf"]
    assert reranked[0].score == 0.93
    assert reranked[0].metadata["reranker"] == "llm_structured"
    assert reranked[0].metadata["original_score"] == 0.005


def test_fallback_reranking_returns_top_docs_when_threshold_filters_all():
    config = RetrievalAgentConfig(reranker_model="llm", rerank_threshold=0.5, rerank_top_k=2)
    agent = RetrievalAgent(config=config)

    reranked = agent._fallback_reranking("quy định xét tuyển sinh", _docs())

    assert len(reranked) == 2
    assert reranked[0].filename == "doc-1.pdf"


class LowScoreLLM:
    async def generate(self, messages, temperature=0.7, max_tokens=2000, **kwargs):
        return """
        {
          "rankings": [
            {"index": 1, "score": 0.25, "reason": "weak lexical overlap"},
            {"index": 2, "score": 0.10, "reason": "mostly unrelated"}
          ]
        }
        """


@pytest.mark.asyncio
async def test_llm_reranking_filters_documents_below_threshold():
    config = RetrievalAgentConfig(reranker_model="llm", rerank_threshold=0.8, rerank_top_k=3)
    agent = RetrievalAgent(config=config, llm_client=FakeLLM())

    reranked = await agent._rerank_documents("quy định xét tuyển sinh", _docs())

    assert [doc.filename for doc in reranked] == ["doc-3.pdf", "doc-1.pdf"]
    assert all(doc.score >= 0.8 for doc in reranked)


@pytest.mark.asyncio
async def test_llm_reranking_keeps_single_best_candidate_when_all_scores_low():
    config = RetrievalAgentConfig(reranker_model="llm", rerank_threshold=0.8, rerank_top_k=3)
    agent = RetrievalAgent(config=config, llm_client=LowScoreLLM())

    reranked = await agent._rerank_documents("quy định xét tuyển sinh", _docs())

    assert len(reranked) == 1
    assert reranked[0].filename == "doc-2.pdf"
    assert reranked[0].metadata["reranker"] == "llm_structured_threshold_fallback"


@pytest.mark.asyncio
async def test_tei_reranking_runs_during_search_without_llm_call():
    doc_id = uuid4()
    embedding = AsyncMock()
    embedding.embed.return_value = [0.1] * 1024
    search = AsyncMock()
    search.execute.return_value = [
        {
            "document_id": str(doc_id),
            "text": "Relevant document",
            "score": 0.2,
            "rerank_score": 0.9,
            "metadata": {},
        }
    ]
    llm = AsyncMock()
    agent = RetrievalAgent(
        config=RetrievalAgentConfig(reranker_model="tei", rerank_top_k=2),
        llm_client=llm,
        embedding=embedding,
        search=search,
    )

    retrieved, _ = await agent._retrieve_documents(["query"], "user-1")
    reranked = await agent._rerank_documents("query", retrieved)

    assert search.execute.await_args.kwargs["k"] == 2
    assert reranked[0].score == 0.9
    assert reranked[0].metadata["reranker"] == "tei"
    llm.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_llm_reranking_uses_candidate_search_before_llm():
    doc_id = uuid4()
    embedding = AsyncMock()
    embedding.embed.return_value = [0.1] * 1024
    search = AsyncMock()
    search.execute_candidates.return_value = [
        {
            "document_id": str(doc_id),
            "text": "Relevant document",
            "score": 0.2,
            "metadata": {},
        }
    ]
    agent = RetrievalAgent(
        config=RetrievalAgentConfig(reranker_model="llm", top_k=10),
        llm_client=FakeLLM(),
        embedding=embedding,
        search=search,
    )

    retrieved, _ = await agent._retrieve_documents(["query"], "user-1")

    assert len(retrieved) == 1
    assert search.execute_candidates.await_args.kwargs["k"] == 10
    search.execute.assert_not_awaited()
