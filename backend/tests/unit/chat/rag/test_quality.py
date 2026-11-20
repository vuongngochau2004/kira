"""LLM grounding check that drives RAG answer verification in the quality gate."""

from types import SimpleNamespace
from typing import Any

import pytest

from kira.chat.rag.nodes.quality import QualityAgent
from kira.chat.rag.state import QualityAgentConfig

DOCS = [
    SimpleNamespace(filename="quy-dinh.txt", content="Nghỉ 12 ngày phép năm hưởng nguyên lương.")
]
ANSWER = "Viên chức làm việc đủ 12 tháng được nghỉ 12 ngày phép năm hưởng nguyên lương."


class FakeLLM:
    """Return a fixed completion and record prompts."""

    def __init__(self, reply: str | Exception) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    async def generate(self, messages: list[dict[str, Any]], **_: Any) -> str:
        self.prompts.append(messages[0]["content"])
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def _agent(llm: FakeLLM | None) -> QualityAgent:
    return QualityAgent(QualityAgentConfig(), llm_client=llm)


@pytest.mark.asyncio
async def test_grounded_answer_passes_verification_threshold() -> None:
    agent = _agent(FakeLLM('```json\n{"grounding_score": 1.0, "unsupported_claims": []}\n```'))
    critique = agent._rule_based_critique(ANSWER, DOCS)

    result = await agent._verify_response("Nghỉ phép bao nhiêu ngày?", ANSWER, DOCS, critique)

    assert result.factual_consistency == 1.0
    assert result.is_verified is True


@pytest.mark.asyncio
async def test_ungrounded_answer_fails_verification() -> None:
    agent = _agent(FakeLLM('{"grounding_score": 0.3, "unsupported_claims": ["20 ngày phép"]}'))
    critique = agent._rule_based_critique(ANSWER, DOCS)

    result = await agent._verify_response("Nghỉ phép bao nhiêu ngày?", ANSWER, DOCS, critique)

    assert result.factual_consistency == 0.3
    assert result.is_verified is False


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_heuristic() -> None:
    agent = _agent(FakeLLM(RuntimeError("timeout")))

    score = await agent._verify_factual_consistency("q", ANSWER, DOCS)

    assert score == agent._heuristic_factual_consistency(ANSWER)


@pytest.mark.asyncio
async def test_no_documents_skips_llm_grounding() -> None:
    llm = FakeLLM('{"grounding_score": 1.0}')
    agent = _agent(llm)

    score = await agent._verify_factual_consistency("q", ANSWER, [])

    assert llm.prompts == []
    assert score == agent._heuristic_factual_consistency(ANSWER)


@pytest.mark.asyncio
async def test_short_grounded_answer_is_not_dragged_down_by_heuristics() -> None:
    """Grounding 0.85 must verify even when length/citation heuristics are low."""
    agent = _agent(FakeLLM('{"grounding_score": 0.85, "unsupported_claims": []}'))
    short_answer = "8 năm."
    critique = agent._rule_based_critique(short_answer, DOCS)

    result = await agent._verify_response("Tối đa mấy năm?", short_answer, DOCS, critique)

    assert result.reasoning_quality < 0.8  # heuristic alone would have failed the threshold
    assert result.confidence == 0.85
    assert result.is_verified is True


@pytest.mark.asyncio
async def test_unsupported_claims_are_reported_in_verification_checks() -> None:
    agent = _agent(
        FakeLLM('{"grounding_score": 0.5, "unsupported_claims": ["tối đa 14 TC cho mọi SV"]}')
    )
    critique = agent._rule_based_critique(ANSWER, DOCS)

    result = await agent._verify_response("Tối đa bao nhiêu TC?", ANSWER, DOCS, critique)

    assert result.is_verified is False
    assert "Unsupported claim: tối đa 14 TC cho mọi SV" in result.verification_checks


@pytest.mark.asyncio
async def test_heuristic_fallback_keeps_weighted_confidence() -> None:
    agent = _agent(FakeLLM(RuntimeError("timeout")))
    critique = agent._rule_based_critique(ANSWER, DOCS)

    result = await agent._verify_response("q", ANSWER, DOCS, critique)

    expected = (
        result.factual_consistency * 0.4
        + result.citation_accuracy * 0.3
        + result.reasoning_quality * 0.3
    )
    assert result.confidence == pytest.approx(expected)


@pytest.mark.asyncio
async def test_grounding_prompt_flags_wrong_condition_and_omissions() -> None:
    llm = FakeLLM('{"grounding_score": 1.0}')
    agent = _agent(llm)

    await agent._verify_factual_consistency("q", ANSWER, DOCS)

    assert "áp sai đối tượng/điều kiện" in llm.prompts[0]
    assert "bỏ sót" in llm.prompts[0]
