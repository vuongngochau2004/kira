"""Tests for kira.chat.rag.pipeline."""

import json

import pytest

from kira.chat.rag.pipeline import RAGPipelineService
from kira.chat.rag.state import AgentResult, AgentStatus


class FakeWorkflow:
    llm = None

    async def run(self, query, user_id, conversation_id=None):
        return {
            "final_response": "Không tìm thấy thông tin phù hợp.",
            "final_citations": [],
            "agent_results": [
                AgentResult(
                    agent_name="RetrievalAgent", status=AgentStatus.COMPLETED, execution_time_ms=3
                )
            ],
        }

    async def run_stream(self, query, user_id, conversation_id=None):
        if False:
            yield {}


@pytest.mark.asyncio
async def test_rag_result_metadata_is_json_serializable():
    result = await RAGPipelineService(FakeWorkflow()).execute("câu hỏi", "user-1")

    assert result.rejected is True
    assert result.metadata["agent_results"][0]["agent_name"] == "RetrievalAgent"
    json.dumps(result.metadata)
