"""Resolve the reference date(s) of a legal question: rules first, LLM when unsure."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import date

from src.modules.legal.domain.temporal import (
    TemporalQuery,
    default_temporal_query,
    resolve_temporal_rules,
)
from src.modules.legal.domain.temporal.llm import build_temporal_messages, parse_temporal_response
from src.shared.ports.llm import LLMPort
from src.shared.utils.agent import parse_json_response

logger = logging.getLogger(__name__)

FALLBACK_REASON = "temporal reference unclear; using today"


class ResolveTemporalQuery:
    def __init__(self, llm: LLMPort, today: Callable[[], date]) -> None:
        self._llm = llm
        self._today = today

    async def execute(self, question: str) -> TemporalQuery:
        today = self._today()
        ruled = resolve_temporal_rules(question, today)
        if ruled is not None:
            return ruled
        parsed: TemporalQuery | None = None
        try:
            response = await self._llm.generate(
                build_temporal_messages(question, today), temperature=0.0, max_tokens=200
            )
            parsed = parse_temporal_response(parse_json_response(response), today)
        except Exception as exc:  # the answer must not fail because date resolution did
            logger.warning("LLM temporal resolution failed: %s", exc)
        if parsed is not None:
            return parsed
        return replace(default_temporal_query(today), reason=FALLBACK_REASON)
