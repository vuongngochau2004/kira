"""LLM fallback for resolving the reference date(s) of a legal question."""

from collections.abc import Mapping
from datetime import date
from typing import Any

from src.modules.legal.domain.temporal.rules import TemporalQuery

EARLIEST_LEGAL_DATE = date(1945, 9, 2)
_EXPECTED_DATES = {"single": 1, "compare": 2}


def build_temporal_messages(question: str, today: date) -> list[dict[str, str]]:
    system = (
        "You determine which date(s) a Vietnamese legal question refers to, so the answer uses the "
        f"law in force on that date. Today is {today.isoformat()}. "
        "Return only JSON: "
        '{"mode": "single" | "compare", "dates": ["YYYY-MM-DD", ...], "reason": str}. '
        'Use "single" with one date when the question asks about one moment (today when none is '
        'given). Use "compare" with exactly two dates when it compares two moments '
        '(before/after a change). "Trước ngày X" means the day before X. '
        "When the question refers to an event such as a law taking effect, use that law's "
        "effective date as you know it."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Question: {question}"},
    ]


def parse_temporal_response(payload: Mapping[str, Any], today: date) -> TemporalQuery | None:
    """Return a TemporalQuery only when the payload is fully valid."""
    mode = payload.get("mode") if isinstance(payload, Mapping) else None
    raw_dates = payload.get("dates") if isinstance(payload, Mapping) else None
    if mode not in _EXPECTED_DATES or not isinstance(raw_dates, list):
        return None
    try:
        dates = tuple(sorted({date.fromisoformat(str(value)) for value in raw_dates}))
    except ValueError:
        return None
    if len(dates) != _EXPECTED_DATES[mode]:
        return None
    latest_allowed = date(today.year + 5, 12, 31)
    if any(day < EARLIEST_LEGAL_DATE or day > latest_allowed for day in dates):
        return None
    reason = str(payload.get("reason") or "llm")[:200]
    return TemporalQuery(mode=mode, dates=dates, reason=reason, source="llm")
