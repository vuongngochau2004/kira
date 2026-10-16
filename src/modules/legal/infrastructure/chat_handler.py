"""Chat handler for the legal_qa intent: maps use-case events to the SSE chunk contract."""

import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from src.modules.legal.application.answer_question import (
    AnswerLegalQuestion,
    LegalQAResult,
    LegalQAStatus,
    LegalQAToken,
)
from src.shared.ports.classification import ClassificationResult, Intent
from src.shared.ports.handlers import Citation, HandlerConfig, HandlerResult, QueryHandlerBase

logger = logging.getLogger(__name__)

LEGAL_QA_UNAVAILABLE_MESSAGE = "Chức năng tra cứu pháp luật đang tạm ngưng. Vui lòng thử lại sau."


class LegalQAHandler(QueryHandlerBase):
    def __init__(self, service: AnswerLegalQuestion, config: HandlerConfig | None = None) -> None:
        self._service = service
        self._config = config or HandlerConfig()

    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict]:
        try:
            async for event in self._service.stream(query):
                if isinstance(event, LegalQAStatus):
                    yield {
                        "type": "status",
                        "data": {"stage": event.stage, "metadata": event.metadata},
                    }
                elif isinstance(event, LegalQAToken):
                    yield {"type": "content", "data": {"text": event.text}}
                elif isinstance(event, LegalQAResult):
                    yield {"type": "metadata", "data": _metadata(event)}
        except Exception:
            logger.exception("Legal QA failed for user %s", user_id)
            yield {"type": "content", "data": {"text": LEGAL_QA_UNAVAILABLE_MESSAGE}}
            yield {
                "type": "metadata",
                "data": {"citations": [], "sources": [], "legal": {"error": "unavailable"}},
            }
        yield {"type": "done"}

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None,
    ) -> HandlerResult:
        parts: list[str] = []
        metadata: dict[str, Any] = {}
        async for chunk in self.handle_stream(query, user_id, classification, context):
            if chunk["type"] == "content":
                parts.append(chunk["data"]["text"])
            elif chunk["type"] == "metadata":
                metadata = chunk["data"]
        citations = [
            Citation(
                filename=item["filename"],
                text=item["text"],
                page=item.get("page"),
                confidence=float(item.get("confidence") or 0.0),
                metadata={"legal": item.get("legal"), "chunk_id": item.get("chunk_id")},
            )
            for item in metadata.get("citations", [])
        ]
        return HandlerResult(
            content="".join(parts),
            citations=citations,
            metadata={"legal": metadata.get("legal", {})},
        )

    def can_handle(self, classification: ClassificationResult) -> bool:
        return classification.intent == Intent.LEGAL_QA

    def get_config(self) -> HandlerConfig:
        return self._config

    def get_name(self) -> str:
        return "LegalQAHandler"


def _metadata(result: LegalQAResult) -> dict[str, Any]:
    return {
        "citations": result.citations,
        "sources": result.citations,
        "legal": {
            "mode": result.temporal.mode,
            "dates": [day.isoformat() for day in result.temporal.dates],
            "temporal_source": result.temporal.source,
            "notices": result.notices,
        },
    }
