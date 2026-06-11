"""Tests for GenerationAgent LLM client integration."""

from collections.abc import AsyncIterator

import pytest

from src.modules.rag.domain.agents.generation_agent import GenerationAgent
from src.modules.rag.domain.state.rag_state import (
    DocumentWithScore,
    GenerationAgentConfig,
    create_initial_state,
)


class ChatOnlyLLMClient:
    """Mock the runtime LLMClient interface without legacy generate methods."""

    async def chat_async(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, str]:
        assert messages[0]["role"] == "user"
        assert "Question:" in messages[0]["content"]
        return {"content": "Generated answer from chat_async"}

    async def chat_async_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        assert messages[0]["role"] == "user"
        for chunk in ("Generated ", "stream"):
            yield chunk


def _state_with_docs():
    state = create_initial_state("Quy định xét tốt nghiệp", "user123")
    doc = DocumentWithScore(
        doc_id="00000000-0000-0000-0000-000000000001",
        content="Sinh viên đủ điều kiện tốt nghiệp khi hoàn thành chương trình đào tạo.",
        filename="regulation.pdf",
        page_number=1,
        chunk_index=0,
        score=0.95,
    )
    state["retrieval_agent_output"]["reranked_docs"] = [doc.model_dump()]
    return state


@pytest.mark.asyncio
async def test_generation_agent_uses_chat_async_client_interface():
    agent = GenerationAgent(
        config=GenerationAgentConfig(),
        llm_client=ChatOnlyLLMClient(),
    )

    state = await agent.handle(_state_with_docs())

    assert state["generated_response"] == "Generated answer from chat_async"
    assert state["final_response"] == "Generated answer from chat_async"
    assert len(state["final_citations"]) == 1


@pytest.mark.asyncio
async def test_generation_agent_stream_uses_chat_async_stream_client_interface():
    agent = GenerationAgent(
        config=GenerationAgentConfig(),
        llm_client=ChatOnlyLLMClient(),
    )

    chunks = []
    async for chunk in agent.handle_stream(_state_with_docs()):
        chunks.append(chunk)

    content = "".join(
        chunk["data"]["text"]
        for chunk in chunks
        if chunk["type"] == "content"
    )
    metadata = [chunk for chunk in chunks if chunk["type"] == "metadata"]

    assert content == "Generated stream"
    assert metadata
