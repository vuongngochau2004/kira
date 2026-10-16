"""Route questions about the shared legal corpus to the legal_qa intent.

Registered first in the classifier chain only when the legal module is enabled, so legal cues win
over the broad file keywords ("điều", "về", ...) of the keyword strategy.
"""

import re
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from src.shared.ports.classification import (
    ClassificationResult,
    ClassificationStrategyBase,
    Intent,
)

LEGAL_KEYWORD_CONFIDENCE = 0.9
PERSONAL_DOCUMENT_CUES = (
    "tài liệu",
    "tệp",
    "file",
    "pdf",
    "docx",
    "tải lên",
    "đã tải",
    "của tôi",
    "văn bản này",
    "hợp đồng này",
    "quyết định này",
    "quy định này",
    "thông báo này",
    # Internal regulations of the deployment's organisation stay on personal RAG.
    "quy chế",
    "nội quy",
    "của trường",
    "nhà trường",
    "đảng ủy",
)
# Everyday phrases containing "luật" that are not about legislation.
NON_LEGAL_PHRASES = (
    "quy luật",
    "kỷ luật",
    "luật sư",
    "luật chơi",
    "khoa luật",
    "ngành luật",
    "đại học luật",
    "trường luật",
    "sinh viên luật",
)


def _phrase_pattern(phrases: Sequence[str]) -> re.Pattern[str] | None:
    cleaned = sorted({p.strip().lower() for p in phrases if p.strip()}, key=len, reverse=True)
    if not cleaned:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(p) for p in cleaned) + r")(?!\w)")


class LegalKeywordStrategy(ClassificationStrategyBase):
    def __init__(self, keywords: Sequence[str], number_pattern: re.Pattern[str]) -> None:
        self._keywords = _phrase_pattern(keywords)
        self._number_pattern = number_pattern
        self._personal = _phrase_pattern(PERSONAL_DOCUMENT_CUES)
        self._non_legal = _phrase_pattern(NON_LEGAL_PHRASES)

    def _legal_cue(self, query: str) -> str | None:
        number = self._number_pattern.search(query)
        if number is not None:
            return number.group(0)
        if self._keywords is None:
            return None
        lowered = query.lower()
        if self._non_legal is not None:
            lowered = self._non_legal.sub(" ", lowered)
        match = self._keywords.search(lowered)
        return match.group(0) if match else None

    def _is_personal(self, query: str) -> bool:
        return self._personal is not None and self._personal.search(query.lower()) is not None

    def can_handle(self, query: str, user_id: str | UUID) -> bool:
        return self._legal_cue(query) is not None and not self._is_personal(query)

    async def classify(
        self, query: str, user_id: str | UUID, context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        cue = self._legal_cue(query)
        if cue is None or self._is_personal(query):
            return ClassificationResult(
                intent=Intent.RAG,
                confidence=0.0,
                reason="No legal corpus cue",
                metadata={"strategy": "legal_keyword"},
            )
        return ClassificationResult(
            intent=Intent.LEGAL_QA,
            confidence=LEGAL_KEYWORD_CONFIDENCE,
            reason=f"Legal corpus cue: {cue}",
            metadata={"strategy": "legal_keyword", "cue": cue},
            handler_hint="LegalQAHandler",
        )
