import json
from datetime import date

import pytest

from src.modules.legal.application.temporal import FALLBACK_REASON, ResolveTemporalQuery
from src.modules.legal.domain.temporal.llm import build_temporal_messages, parse_temporal_response
from tests.legal_fakes import FakeLLM

TODAY = date(2026, 10, 15)


def _resolver(*responses):
    llm = FakeLLM(*responses)
    return ResolveTemporalQuery(llm, lambda: TODAY), llm


async def test_rules_answer_without_llm() -> None:
    resolver, llm = _resolver()
    result = await resolver.execute("Trước ngày 1/7/2026 quy định thế nào?")
    assert result.dates == (date(2026, 6, 30),)
    assert llm.calls == []


async def test_llm_resolves_relative_reference() -> None:
    payload = {"mode": "compare", "dates": ["2024-08-01", "2024-07-31"], "reason": "trước/sau"}
    resolver, llm = _resolver(json.dumps(payload))
    result = await resolver.execute("Trước khi Luật Đất đai 2024 có hiệu lực thì sao?")
    assert (result.mode, result.dates, result.source) == (
        "compare",
        (date(2024, 7, 31), date(2024, 8, 1)),
        "llm",
    )
    assert "2026-10-15" in llm.calls[0][0]["content"]


@pytest.mark.parametrize(
    "response",
    [
        json.dumps({"mode": "single", "dates": ["3000-01-01"]}),
        json.dumps({"mode": "single", "dates": ["2025-01-01", "2026-01-01"]}),
        json.dumps({"mode": "compare", "dates": ["2025-01-01"]}),
        json.dumps({"mode": "range", "dates": ["2025-01-01"]}),
        json.dumps({"mode": "single", "dates": ["01/01/2025"]}),
        "không phải JSON",
        RuntimeError("timeout"),
    ],
)
async def test_invalid_llm_output_falls_back_to_today(response) -> None:
    resolver, _ = _resolver(response)
    result = await resolver.execute("So sánh luật cũ và mới về thuế")
    assert (result.mode, result.dates, result.source) == ("single", (TODAY,), "default")
    assert result.reason == FALLBACK_REASON


def test_parse_accepts_valid_single() -> None:
    parsed = parse_temporal_response(
        {"mode": "single", "dates": ["2025-12-31"], "reason": "r"}, TODAY
    )
    assert parsed is not None and parsed.dates == (date(2025, 12, 31),)


def test_messages_state_today_and_schema() -> None:
    messages = build_temporal_messages("câu hỏi", TODAY)
    assert messages[0]["role"] == "system"
    assert '"mode"' in messages[0]["content"]
    assert messages[1]["content"].endswith("câu hỏi")
