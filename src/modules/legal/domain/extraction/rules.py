"""Rule-based extraction of legal relation candidates from parsed documents."""

import re
from collections.abc import Iterator

from src.modules.legal.domain.models import (
    ParsedProvision,
    ParseResult,
    ProvisionLevel,
    RelationDraft,
    RelationType,
)
from src.modules.legal.domain.provision_key import (
    iter_vietnamese_ref_groups,
    iter_vietnamese_refs,
    parse_vietnamese_ref,
)

DOCUMENT_NUMBER_PATTERN = re.compile(
    r"(?<![\w/])(\d{1,4}/\d{4}/[A-ZĐ][A-ZĐ0-9]*(?:-[A-ZĐ0-9]+)*)(?![\w/-])"
)

BASED_ON_CONFIDENCE = 0.95
REPLACES_CONFIDENCE = 0.9
EXPIRES_CONFIDENCE = 0.85
REPEALS_CONFIDENCE = 0.85
GUIDES_CONFIDENCE = 0.8
AMENDS_CONFIDENCE = 0.7

_REPLACES = re.compile(r"\bthay\s+thế\b(?!\s+(?:cụm\s+)?từ\b)", re.IGNORECASE)
_EXPIRES = re.compile(r"\bhết\s+hiệu\s+lực\b", re.IGNORECASE)
_REPEALS = re.compile(r"\bbãi\s+bỏ\b", re.IGNORECASE)
_GUIDES = re.compile(
    r"\b(?:quy\s+định\s+chi\s+tiết|hướng\s+dẫn(?:\s+thi\s+hành)?)\b", re.IGNORECASE
)
_AMEND_VERB = re.compile(r"\b(?:sửa\s+đổi|bổ\s+sung)\b", re.IGNORECASE)
_INSERTION = re.compile(
    r"\bbổ\s+sung\s+(?:điểm\s+(?P<point>[a-zđ])|khoản\s+(?P<clause>\d+[a-zđ]?))\s+vào\b",
    re.IGNORECASE,
)
_QUOTED_CURLY = re.compile(r"“(.*?)”", re.DOTALL)
_QUOTED_STRAIGHT = re.compile(r'"(.*?)"', re.DOTALL)
_SENTENCE_SPLIT = re.compile(r"[.;\n]+")

_TAIL_RULES: tuple[tuple[re.Pattern[str], RelationType, float, bool], ...] = (
    (_REPLACES, RelationType.REPLACES, REPLACES_CONFIDENCE, False),
    (_REPEALS, RelationType.REPEALS, REPEALS_CONFIDENCE, True),
    (_GUIDES, RelationType.GUIDES, GUIDES_CONFIDENCE, True),
)


def find_document_numbers(text: str) -> list[str]:
    return [match.group(1) for match in DOCUMENT_NUMBER_PATTERN.finditer(text)]


def extract_rule_candidates(result: ParseResult, own_number: str) -> list[RelationDraft]:
    """Propose relation candidates using deterministic Vietnamese legal phrasing."""
    drafts: list[RelationDraft] = list(_based_on(result.preamble, own_number))
    by_key = {provision.provision_key: provision for provision in result.provisions}
    for provision in result.provisions:
        drafts.extend(_sentence_relations(provision, own_number))
        amendment = _amendment(provision, by_key, own_number)
        if amendment is not None:
            drafts.append(amendment)
    return _dedupe(drafts)


def _based_on(preamble: str, own_number: str) -> Iterator[RelationDraft]:
    for line in preamble.splitlines():
        stripped = line.strip()
        if not stripped.lower().startswith("căn cứ"):
            continue
        for number in find_document_numbers(stripped):
            if number != own_number:
                yield RelationDraft(
                    type=RelationType.BASED_ON,
                    target_number=number,
                    evidence_text=stripped,
                    confidence=BASED_ON_CONFIDENCE,
                )


def _sentence_relations(provision: ParsedProvision, own_number: str) -> Iterator[RelationDraft]:
    text = _QUOTED_STRAIGHT.sub(" ", _QUOTED_CURLY.sub(" ", provision.text))
    for raw_sentence in _SENTENCE_SPLIT.split(text):
        sentence = raw_sentence.strip()
        if not sentence:
            continue
        if _EXPIRES.search(sentence):
            for number in find_document_numbers(sentence):
                if number != own_number:
                    yield _draft(
                        provision,
                        RelationType.REPLACES,
                        number,
                        None,
                        sentence,
                        EXPIRES_CONFIDENCE,
                    )
        for pattern, relation_type, confidence, uses_refs in _TAIL_RULES:
            match = pattern.search(sentence)
            if match is None:
                continue
            tail = sentence[match.end() :]
            segment_start = 0
            for number_match in DOCUMENT_NUMBER_PATTERN.finditer(tail):
                number = number_match.group(1)
                segment = tail[segment_start : number_match.start()]
                segment_start = number_match.end()
                if number == own_number:
                    continue
                refs: list[str | None] = list(iter_vietnamese_refs(segment)) if uses_refs else []
                for ref in refs or [None]:
                    yield _draft(provision, relation_type, number, ref, sentence, confidence)


def _amendment(
    provision: ParsedProvision, by_key: dict[str, ParsedProvision], own_number: str
) -> RelationDraft | None:
    if provision.level is ProvisionLevel.POINT:
        return None
    lines = provision.text.splitlines()
    instruction = provision.heading if provision.level is ProvisionLevel.ARTICLE else lines[0]
    if not instruction.rstrip().endswith(":") or not _AMEND_VERB.search(instruction):
        return None
    ref = _amendment_target_ref(instruction)
    quoted = _QUOTED_CURLY.search(provision.text) or _QUOTED_STRAIGHT.search(provision.text)
    if ref is None or quoted is None or not quoted.group(1).strip():
        return None

    target_number = _first_foreign_number(instruction, own_number)
    parent = by_key.get(provision.parent_key) if provision.parent_key else None
    if target_number is None and parent is not None:
        target_number = _first_foreign_number(parent.text, own_number)
    if target_number is None:
        return None

    return RelationDraft(
        type=RelationType.AMENDS,
        target_number=target_number,
        evidence_text=instruction.strip(),
        confidence=AMENDS_CONFIDENCE,
        source_provision_key=provision.provision_key,
        target_provision_ref=ref,
        new_text=quoted.group(1).strip(),
        evidence_page=provision.page,
    )


def _amendment_target_ref(instruction: str) -> str | None:
    """Return the single provision an instruction amends, or None when ambiguous."""
    insertion = _INSERTION.search(instruction)
    if insertion is not None:
        container = parse_vietnamese_ref(instruction[insertion.end() :])
        if container is None:
            return None
        if insertion.group("point"):
            if ".K" not in container or container.count(".") > 1:
                return None
            return f"{container}.{insertion.group('point').lower()}"
        article = container.split(".")[0]
        return f"{article}.K{insertion.group('clause').lower()}"
    groups = list(iter_vietnamese_ref_groups(instruction))
    if not groups or len(groups[0]) != 1:
        return None
    return groups[0][0]


def _first_foreign_number(text: str, own_number: str) -> str | None:
    return next((n for n in find_document_numbers(text) if n != own_number), None)


def _draft(
    provision: ParsedProvision,
    relation_type: RelationType,
    number: str,
    ref: str | None,
    sentence: str,
    confidence: float,
) -> RelationDraft:
    return RelationDraft(
        type=relation_type,
        target_number=number,
        evidence_text=sentence,
        confidence=confidence,
        source_provision_key=provision.provision_key,
        target_provision_ref=ref,
        evidence_page=provision.page,
    )


def _dedupe(drafts: list[RelationDraft]) -> list[RelationDraft]:
    seen: set[tuple[object, ...]] = set()
    unique: list[RelationDraft] = []
    for draft in drafts:
        key = (
            draft.type,
            draft.source_provision_key,
            draft.target_number,
            draft.target_provision_ref,
            draft.new_text,
        )
        if key not in seen:
            seen.add(key)
            unique.append(draft)
    return unique
