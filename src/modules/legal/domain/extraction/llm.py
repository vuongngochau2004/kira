"""LLM-assisted extraction of amendment relations, with strict validation."""

import re
from collections.abc import Mapping, Sequence
from typing import Any

from src.modules.legal.domain.extraction.rules import DOCUMENT_NUMBER_PATTERN
from src.modules.legal.domain.models import (
    ParsedProvision,
    ParseResult,
    ProvisionLevel,
    RelationDraft,
    RelationType,
)
from src.modules.legal.domain.provision_key import is_valid_provision_ref

LLM_AMENDMENT_CONFIDENCE = 0.6

_AMEND_VERB = re.compile(r"\b(?:sửa\s+đổi|bổ\s+sung)\b", re.IGNORECASE)
_QUOTE_MARK = re.compile(r"[“\"]")

AMENDMENT_SYSTEM_PROMPT = (
    "You extract amendments from Vietnamese legal documents. Each provision below may instruct "
    "to amend or supplement (sửa đổi, bổ sung) one provision of another legal document. "
    "Return only JSON of the form "
    '{"amendments": [{"source_provision_key": str, "target_number": str, '
    '"target_provision_ref": str, "new_text": str}]}. '
    "source_provision_key is the key after ### of the provision giving the instruction. "
    "target_number is the amended document number, for example 31/2024/QH15. "
    "target_provision_ref has the format D<article>[.K<clause>[.<point>]], for example D12.K3.a. "
    "new_text is the quoted new content copied verbatim, without the quotation marks. "
    "Skip a provision when its target document or provision cannot be determined or when it "
    "changes several provisions at once. "
    'Return {"amendments": []} when nothing applies.'
)


def select_amendment_provisions(
    result: ParseResult, covered_source_keys: set[str], limit: int
) -> list[ParsedProvision]:
    """Provisions that look like amendment instructions not already handled by rules."""
    selected: list[ParsedProvision] = []
    for provision in result.provisions:
        if provision.level is ProvisionLevel.POINT:
            continue
        if provision.provision_key in covered_source_keys:
            continue
        if _AMEND_VERB.search(_instruction(provision)) and _QUOTE_MARK.search(provision.text):
            selected.append(provision)
            if len(selected) >= limit:
                break
    return selected


def build_amendment_messages(
    result: ParseResult, provisions: Sequence[ParsedProvision], own_number: str
) -> list[dict[str, str]]:
    by_key = {provision.provision_key: provision for provision in result.provisions}
    blocks: list[str] = []
    for provision in provisions:
        parent = by_key.get(provision.parent_key) if provision.parent_key else None
        context = parent.text.splitlines()[0] if parent else ""
        blocks.append(f"### {provision.provision_key}\nContext: {context}\n{provision.text}")
    user = f"Document number: {own_number}\n\n" + "\n\n".join(blocks)
    return [
        {"role": "system", "content": AMENDMENT_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def parse_amendment_response(
    payload: Mapping[str, Any], provisions: Sequence[ParsedProvision], own_number: str
) -> list[RelationDraft]:
    """Validate LLM output; drop items that are not grounded in the source provision."""
    items = payload.get("amendments") if isinstance(payload, Mapping) else None
    if not isinstance(items, list):
        raise ValueError("LLM response has no 'amendments' list")

    by_key = {provision.provision_key: provision for provision in provisions}
    drafts: list[RelationDraft] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        source = by_key.get(str(item.get("source_provision_key", "")).strip())
        number = str(item.get("target_number", "")).strip()
        ref = str(item.get("target_provision_ref", "")).strip()
        new_text = str(item.get("new_text", "")).strip().strip('“”"').strip()
        if source is None or not new_text or not is_valid_provision_ref(ref):
            continue
        if number == own_number or DOCUMENT_NUMBER_PATTERN.fullmatch(number) is None:
            continue
        if _normalize(new_text) not in _normalize(source.text):
            continue
        drafts.append(
            RelationDraft(
                type=RelationType.AMENDS,
                target_number=number,
                evidence_text=_instruction(source).strip(),
                confidence=LLM_AMENDMENT_CONFIDENCE,
                source_provision_key=source.provision_key,
                target_provision_ref=ref,
                new_text=new_text,
                evidence_page=source.page,
                extractor="llm",
            )
        )
    return drafts


def _instruction(provision: ParsedProvision) -> str:
    if provision.level is ProvisionLevel.ARTICLE:
        return provision.heading
    return provision.text.splitlines()[0] if provision.text else ""


def _normalize(text: str) -> str:
    return " ".join(text.replace("“", " ").replace("”", " ").replace('"', " ").split())
