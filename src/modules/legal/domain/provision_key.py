"""Stable provision keys and parsing of Vietnamese provision references."""

import re
from collections.abc import Iterator

from src.modules.legal.domain.models import ProvisionLevel

_LIST_SEPARATOR = r"\s*(?:,|và)\s*"
_REF_PATTERN = re.compile(
    r"(?:(?:các\s+)?điểm\s+(?P<points>[a-zđ]\b"
    r"(?:" + _LIST_SEPARATOR + r"(?:điểm\s+)?[a-zđ]\b)*)\s+)?"
    r"(?:(?:các\s+)?khoản\s+(?P<clauses>\d+[a-zđ]?\b"
    r"(?:" + _LIST_SEPARATOR + r"(?:khoản\s+)?\d+[a-zđ]?\b)*)\s+)?"
    r"điều\s+(?P<article>\d+[a-zđ]?)\b",
    re.IGNORECASE,
)
_LIST_ITEM = re.compile(r"(?:điểm|khoản)\s+|" + _LIST_SEPARATOR, re.IGNORECASE)


def build_provision_ref(article: str, clause: str | None = None, point: str | None = None) -> str:
    """Build the part of a provision key after '#', e.g. 'D12.K3.a'."""
    if point is not None and clause is None:
        raise ValueError("A point reference requires a clause")
    ref = f"D{article}"
    if clause is not None:
        ref += f".K{clause}"
    if point is not None:
        ref += f".{point}"
    return ref


def build_provision_key(
    number: str, article: str, clause: str | None = None, point: str | None = None
) -> str:
    """Build a full provision key, e.g. '31/2024/QH15#D12.K3.a'."""
    return f"{number}#{build_provision_ref(article, clause, point)}"


def iter_vietnamese_ref_groups(text: str) -> Iterator[list[str]]:
    """Yield one list of refs per phrase; lists like 'khoản 2 và khoản 3 Điều 5' expand."""
    for match in _REF_PATTERN.finditer(text):
        article = match.group("article").lower()
        clauses = _split_items(match.group("clauses"))
        points = _split_items(match.group("points"))
        if not clauses:
            yield [build_provision_ref(article)]
        elif points and len(clauses) == 1:
            yield [build_provision_ref(article, clauses[0], point) for point in points]
        else:
            yield [build_provision_ref(article, clause) for clause in clauses]


def iter_vietnamese_refs(text: str) -> Iterator[str]:
    """Yield provision refs for phrases like 'điểm a khoản 3 Điều 12'."""
    for group in iter_vietnamese_ref_groups(text):
        yield from group


def _split_items(items: str | None) -> list[str]:
    if not items:
        return []
    return [item.lower() for item in _LIST_ITEM.split(items) if item.strip()]


def parse_vietnamese_ref(text: str) -> str | None:
    """Return the first provision ref found in text, or None."""
    return next(iter_vietnamese_refs(text), None)


PROVISION_REF_PATTERN = re.compile(r"D\d+[a-zđ]?(?:\.K\d+[a-zđ]?(?:\.[a-zđ])?)?")


def is_valid_provision_ref(ref: str) -> bool:
    return PROVISION_REF_PATTERN.fullmatch(ref) is not None


def split_provision_key(key: str) -> tuple[str, str]:
    """Split '31/2024/QH15#D3.K1' into ('31/2024/QH15', 'D3.K1')."""
    number, separator, ref = key.partition("#")
    if not separator or not number or not is_valid_provision_ref(ref):
        raise ValueError(f"Invalid provision key: {key}")
    return number, ref


def describe_provision_ref(ref: str) -> tuple[ProvisionLevel, str, str | None]:
    """Return (level, Vietnamese label, parent ref) for a provision ref."""
    if not is_valid_provision_ref(ref):
        raise ValueError(f"Invalid provision ref: {ref}")
    parts = ref.split(".")
    if len(parts) == 1:
        return ProvisionLevel.ARTICLE, f"Điều {parts[0][1:]}", None
    if len(parts) == 2:
        return ProvisionLevel.CLAUSE, f"Khoản {parts[1][1:]}", parts[0]
    return ProvisionLevel.POINT, f"Điểm {parts[2]}", ".".join(parts[:2])
