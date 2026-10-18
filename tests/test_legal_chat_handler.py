from datetime import date

from src.modules.chat.api.endpoints import PERSISTED_METADATA_KEYS
from src.modules.legal.application.answer_question import (
    LegalQAResult,
    LegalQAStatus,
    LegalQAToken,
)
from src.modules.legal.domain.temporal import TemporalQuery
from src.modules.legal.infrastructure.chat_handler import (
    LEGAL_QA_UNAVAILABLE_MESSAGE,
    LegalQAHandler,
)
from src.shared.ports.classification import ClassificationResult, Intent

TEMPORAL = TemporalQuery("single", (date(2026, 10, 15),), "present tense", "rule")
CITATION = {
    "filename": "Khoản 1 — Luật Đất đai (31/2024/QH15)",
    "text": "1. Nội dung.",
    "page": None,
    "confidence": 0.5,
    "chunk_id": "v1",
    "legal": {"provision_key": "31/2024/QH15#D3.K1", "role": "primary"},
}
LEGAL = ClassificationResult(intent=Intent.LEGAL_QA, confidence=0.9)


class FakeService:
    def __init__(self, events, fail_after: int | None = None) -> None:
        self.events = events
        self.fail_after = fail_after

    async def stream(self, question):
        for index, event in enumerate(self.events):
            if self.fail_after is not None and index == self.fail_after:
                raise ConnectionError("qdrant down")
            yield event


EVENTS = [
    LegalQAStatus("temporal", {"mode": "single", "dates": ["2026-10-15"], "source": "rule"}),
    LegalQAToken("Áp dụng tại ngày 15/10/2026. "),
    LegalQAToken("Nội dung [1]."),
    LegalQAResult(TEMPORAL, [CITATION], ["ghi chú"]),
]


async def _chunks(handler):
    return [chunk async for chunk in handler.handle_stream("q", "u1", LEGAL, None)]


async def test_stream_maps_events_to_sse_chunks() -> None:
    chunks = await _chunks(LegalQAHandler(FakeService(EVENTS)))
    assert [c["type"] for c in chunks] == ["status", "content", "content", "metadata", "done"]
    assert chunks[0]["data"] == {
        "stage": "temporal",
        "metadata": {"mode": "single", "dates": ["2026-10-15"], "source": "rule"},
    }
    metadata = chunks[3]["data"]
    assert metadata["citations"] == [CITATION] == metadata["sources"]
    assert metadata["legal"] == {
        "mode": "single",
        "dates": ["2026-10-15"],
        "temporal_source": "rule",
        "notices": ["ghi chú"],
    }


async def test_failure_still_emits_one_metadata_and_done() -> None:
    chunks = await _chunks(LegalQAHandler(FakeService(EVENTS, fail_after=2)))
    types = [c["type"] for c in chunks]
    assert types.count("metadata") == 1 and types[-1] == "done"
    assert chunks[-3]["data"]["text"] == LEGAL_QA_UNAVAILABLE_MESSAGE
    assert chunks[-2]["data"]["citations"] == []


async def test_handle_collects_result() -> None:
    result = await LegalQAHandler(FakeService(EVENTS)).handle("q", "u1", LEGAL)
    assert result.content == "Áp dụng tại ngày 15/10/2026. Nội dung [1]."
    assert result.citations[0].filename == CITATION["filename"]
    assert result.citations[0].metadata["legal"]["provision_key"] == "31/2024/QH15#D3.K1"
    assert result.metadata["legal"]["mode"] == "single"


def test_handler_identity() -> None:
    handler = LegalQAHandler(FakeService([]))
    assert handler.get_name() == "LegalQAHandler"
    assert handler.can_handle(LEGAL)
    assert not handler.can_handle(ClassificationResult(intent=Intent.RAG, confidence=0.9))


def test_legal_metadata_is_persisted() -> None:
    assert "legal" in PERSISTED_METADATA_KEYS
