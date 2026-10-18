"""Rule-based detection of the legal reference date(s) in a user question."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

TemporalMode = Literal["single", "compare"]
TemporalSource = Literal["rule", "default", "llm"]

_NUMERIC_DATE = re.compile(r"(?<![\d/])(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?![\d/])")
_WORD_DATE = re.compile(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", re.IGNORECASE)
_YEAR = re.compile(r"\bnăm\s+(\d{4})\b", re.IGNORECASE)
_DOC_NAME_WITH_YEAR = re.compile(
    r"\b(?:bộ\s+luật|luật|nghị\s+định|thông\s+tư|pháp\s+lệnh|nghị\s+quyết)\b"
    r"(?:\s+số)?(?:\s+\d+(?:/[\w/-]+)?)?[^,.;?!\d]{0,60}?\bnăm\s+\d{4}\b",
    re.IGNORECASE,
)
_YEAR_TEMPORAL_PREFIX = re.compile(
    r"\b(?:vào|trong|từ|đến|tới|cuối|đầu|giữa|tại|ở|trước|sau)\s*$", re.IGNORECASE
)
_BEFORE_DATE_PREFIX = re.compile(r"\btrước\s+(?:ngày\s+)?$", re.IGNORECASE)
_BEFORE_YEAR_PREFIX = re.compile(r"\btrước\s*$", re.IGNORECASE)
_FROM_YEAR_PREFIX = re.compile(r"\b(?:từ|sau)\s*$", re.IGNORECASE)
_COMPARE = re.compile(
    r"so\s+sánh|khác\s+(?:gì|nhau)|thay\s+đổi\s+(?:gì|như\s+thế\s+nào|thế\s+nào)"
    r"|trước\s+và\s+sau|cũ\s+và\s+mới|điểm\s+mới",
    re.IGNORECASE,
)
_PRESENT = re.compile(r"hiện\s+nay|hiện\s+hành|hiện\s+tại|bây\s+giờ", re.IGNORECASE)
_RELATIVE_EVENT = re.compile(r"\b(?:trước|sau)\s+khi\b", re.IGNORECASE)


@dataclass(frozen=True)
class TemporalQuery:
    mode: TemporalMode
    dates: tuple[date, ...]
    reason: str
    source: TemporalSource


@dataclass(frozen=True)
class _Mention:
    raw: date
    resolved: date
    exact: bool = False


def default_temporal_query(today: date) -> TemporalQuery:
    return TemporalQuery(
        mode="single", dates=(today,), reason="no temporal reference", source="default"
    )


def resolve_temporal_rules(question: str, today: date) -> TemporalQuery | None:
    """Resolve the date(s) a legal question refers to; None means uncertain."""
    mentions = _mentions(question, today)
    is_compare = bool(_COMPARE.search(question))

    if is_compare:
        raw_dates = sorted({mention.raw for mention in mentions})
        if len(raw_dates) == 2:
            return TemporalQuery("compare", tuple(raw_dates), "two explicit dates", "rule")
        if len(raw_dates) != 1:
            return None
        if all(mention.exact for mention in mentions):
            pivot = raw_dates[0]
            return TemporalQuery(
                "compare", (pivot - timedelta(days=1), pivot), "before/after one date", "rule"
            )
        year_day = mentions[0].resolved
        if _PRESENT.search(question) and year_day < today:
            return TemporalQuery("compare", (year_day, today), "year versus present", "rule")
        return None

    resolved = sorted({mention.resolved for mention in mentions})
    if resolved and _PRESENT.search(question):
        return None
    if not resolved and _RELATIVE_EVENT.search(question):
        return None
    if len(resolved) == 1:
        return TemporalQuery("single", (resolved[0],), "explicit date", "rule")
    if len(resolved) > 1:
        return None
    if _PRESENT.search(question):
        return TemporalQuery("single", (today,), "present tense", "rule")
    return default_temporal_query(today)


def _mentions(question: str, today: date) -> list[_Mention]:
    mentions: list[_Mention] = []
    date_spans: list[tuple[int, int]] = []

    for pattern in (_NUMERIC_DATE, _WORD_DATE):
        for match in pattern.finditer(question):
            date_spans.append(match.span())
            try:
                raw = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                continue
            before = _BEFORE_DATE_PREFIX.search(question[: match.start()])
            resolved = raw - timedelta(days=1) if before else raw
            mentions.append(_Mention(raw, resolved, exact=True))

    doc_spans = [match.span() for match in _DOC_NAME_WITH_YEAR.finditer(question)]
    for match in _YEAR.finditer(question):
        if _overlaps(match.span(), date_spans):
            continue
        prefix = question[: match.start()]
        if not _YEAR_TEMPORAL_PREFIX.search(prefix) and _overlaps(match.span(), doc_spans):
            continue
        mentions.append(_year_mention(int(match.group(1)), prefix, today))
    return mentions


def _year_mention(year: int, prefix: str, today: date) -> _Mention:
    first_day = date(year, 1, 1)
    if _BEFORE_YEAR_PREFIX.search(prefix):
        return _Mention(first_day, first_day - timedelta(days=1))
    if _FROM_YEAR_PREFIX.search(prefix):
        return _Mention(first_day, first_day)
    if year < today.year:
        day = date(year, 12, 31)
    elif year == today.year:
        day = today
    else:
        day = first_day
    return _Mention(day, day)


def _overlaps(span: tuple[int, int], others: list[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in others)
