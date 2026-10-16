"""Deterministic point-in-time metrics for legal QA answers."""

import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

_EARLIER_ROLES = frozenset({"before", "removed"})
_CITATION_MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_LATER_ROLES = frozenset({"after", "added"})


def _to_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def cited_sources(answer: str, sources: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Sources the answer actually cites with [n] markers (1-based), in first-mention order."""
    order: list[int] = []
    for match in _CITATION_MARKER.finditer(answer):
        for part in match.group(1).split(","):
            index = int(part) - 1
            if 0 <= index < len(sources) and index not in order:
                order.append(index)
    return [sources[index] for index in order]


def _legal_items(citations: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [c["legal"] for c in citations if isinstance(c.get("legal"), Mapping)]


def _in_force(legal: Mapping[str, Any], day: date) -> bool:
    valid_from = _to_date(legal.get("valid_from"))
    valid_to = _to_date(legal.get("valid_to"))
    if valid_from is None:
        return False
    return valid_from <= day and (valid_to is None or day < valid_to)


def temporal_date_accuracy(
    expected_mode: str,
    expected_dates: Sequence[date],
    actual_mode: str,
    actual_dates: Sequence[date],
) -> tuple[float, str]:
    """Share of expected reference dates the resolver produced (0 if the mode differs)."""
    if actual_mode != expected_mode:
        return 0.0, f"Mode {actual_mode} differs from expected {expected_mode}"
    matched = sum(
        1
        for expected, actual in zip(sorted(expected_dates), sorted(actual_dates), strict=False)
        if expected == actual
    )
    score = matched / len(expected_dates) if expected_dates else 1.0
    return score, f"{matched}/{len(expected_dates)} dates match"


def temporal_correctness(
    mode: str, dates: Sequence[date], citations: Sequence[Mapping[str, Any]]
) -> tuple[float, str]:
    """Share of cited versions that are in force on the date(s) they are used for."""
    items = _legal_items(citations)
    if not items:
        return 1.0, "No legal citations"
    ordered = sorted(dates)
    failures: list[str] = []
    for legal in items:
        role = str(legal.get("role", "primary"))
        if mode == "compare" and len(ordered) == 2:
            if role in _EARLIER_ROLES:
                days = [ordered[0]]
            elif role in _LATER_ROLES:
                days = [ordered[1]]
            else:
                days = ordered
        else:
            days = ordered[:1]
        if not all(_in_force(legal, day) for day in days):
            failures.append(f"{legal.get('provision_key')} ({role})")
    score = (len(items) - len(failures)) / len(items)
    reason = (
        "All cited versions in force" if not failures else "Not in force: " + ", ".join(failures)
    )
    return score, reason


def citation_exactness(
    expected_provisions: Sequence[Mapping[str, Any]], citations: Sequence[Mapping[str, Any]]
) -> tuple[float, str]:
    """F1 of cited vs expected provisions (and pinned versions); no-answer samples cite nothing."""
    cited = [
        (str(legal.get("provision_key")), _to_date(legal.get("valid_from")))
        for legal in _legal_items(citations)
    ]
    if not expected_provisions:
        if cited:
            return 0.0, f"Cited {len(cited)} provision(s) for a question with no answer"
        return 1.0, "Correctly cited nothing"

    def matches(expected: Mapping[str, Any], item: tuple[str, date | None]) -> bool:
        wanted = _to_date(expected.get("valid_from"))
        return item[0] == expected.get("provision_key") and (wanted is None or item[1] == wanted)

    found = [e for e in expected_provisions if any(matches(e, item) for item in cited)]
    useful = [item for item in cited if any(matches(e, item) for e in expected_provisions)]
    recall = len(found) / len(expected_provisions)
    precision = len(useful) / len(cited) if cited else 0.0
    score = 2 * recall * precision / (recall + precision) if recall and precision else 0.0
    missing = [str(e.get("provision_key")) for e in expected_provisions if e not in found]
    reason = f"F1 {score:.2f} (recall {recall:.2f}, precision {precision:.2f})"
    if missing:
        reason += "; missing: " + ", ".join(missing)
    return score, reason
