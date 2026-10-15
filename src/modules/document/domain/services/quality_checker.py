"""Text quality analysis and diagnostics for extracted document content.

Provides heuristics for detecting low-quality, corrupt, or garbage text
layers — especially in Vietnamese administrative documents where broken
embedded fonts or encoding artifacts require falling back to OCR.
"""

import logging
import re

from src.modules.document.domain.constants import (
    HTML_ENTITY_PATTERN,
    MOJIBAKE_OR_PLACEHOLDER_PATTERN,
    QUALITY_ISSUE_WEIGHTS,
    VIETNAMESE_DIACRITICS,
    VIETNAMESE_UNACCENTED_SIGNAL_WORDS,
)
from src.modules.document.domain.models import TextQualityReport

logger = logging.getLogger(__name__)


def is_low_quality_text(text: str, lang: str = "vi") -> bool:
    """Detect if the extracted text layer is low-quality, corrupt, or garbage.

    Args:
        text: Extracted text content
        lang: Language for specific diacritics check (default: vi)

    Returns:
        True if the text is low-quality or corrupt, False otherwise
    """
    if not text or not text.strip():
        return True

    cleaned_text = text.strip()
    if len(cleaned_text) < 10:
        return True

    words = cleaned_text.split()
    if len(words) > 5:
        single_char_words = [w for w in words if len(w) == 1 and w.isalpha()]
        if len(single_char_words) / len(words) > 0.40:
            logger.warning(
                "Low quality text detected: excessive single-character words (spacing issue)"
            )
            return True

    if lang == "vi":
        vi_char_count = sum(1 for c in cleaned_text if c.lower() in VIETNAMESE_DIACRITICS)
        total_letters = sum(1 for c in cleaned_text if c.isalpha())

        if total_letters > 20:
            vi_ratio = vi_char_count / total_letters
            if vi_ratio < 0.015:
                logger.warning(
                    "Low quality text detected: very low Vietnamese diacritics ratio (%.2f%%)",
                    vi_ratio * 100,
                )
                return True

    return False


def analyze_vietnamese_text_quality(
    text: str,
    lang: str = "vi",
    fallback_score: int = 3,
) -> TextQualityReport:
    """Analyze whether extracted Vietnamese text should be replaced by OCR.

    Statistical checks detect missing diacritics, placeholder/mojibake characters,
    or leaked HTML entities common in broken Vietnamese text layers.
    """
    if lang != "vi":
        return TextQualityReport(
            issues=[],
            score=0,
            should_fallback=False,
            char_count=len(text),
            word_count=0,
            letter_count=0,
            vi_diacritic_ratio=0.0,
            unaccented_signal_ratio=0.0,
            mojibake_count=0,
            html_entity_count=0,
            alphanumeric_artifact_ratio=0.0,
        )

    issues: list[str] = []
    if is_low_quality_text(text, lang=lang):
        issues.append("low_quality_text")

    words = re.findall(r"[A-Za-zÀ-ỹĐđ]+", text.lower())
    ascii_words = [word for word in words if word.isascii()]
    signal_words = [word for word in ascii_words if word in VIETNAMESE_UNACCENTED_SIGNAL_WORDS]

    letter_count = sum(1 for char in text if char.isalpha())
    vi_ratio = 0.0
    if letter_count:
        vi_ratio = sum(1 for char in text if char.lower() in VIETNAMESE_DIACRITICS) / letter_count

    if letter_count > 400 and vi_ratio < 0.06:
        issues.append("low_vietnamese_diacritics_ratio")

    signal_ratio = 0.0
    if words:
        signal_ratio = len(signal_words) / len(words)
        if len(words) > 80 and signal_ratio > 0.18 and vi_ratio < 0.14:
            issues.append("many_unaccented_vietnamese_terms")

    mojibake_count = len(MOJIBAKE_OR_PLACEHOLDER_PATTERN.findall(text))
    if mojibake_count >= 3:
        issues.append("mojibake_or_placeholder_chars")

    html_entity_count = len(HTML_ENTITY_PATTERN.findall(text))
    if html_entity_count >= 2:
        issues.append("html_entities_in_text")

    odd_ascii_digit_tokens = re.findall(r"\b[A-Za-z]*\d+[A-Za-z]*\b", text)
    alphanumeric_artifact_ratio = 0.0
    if words:
        alphanumeric_artifact_ratio = len(odd_ascii_digit_tokens) / len(words)
    if len(words) > 80 and alphanumeric_artifact_ratio > 0.03:
        issues.append("many_alphanumeric_artifacts")

    issues = sorted(set(issues))
    score = sum(QUALITY_ISSUE_WEIGHTS.get(issue, 1) for issue in issues)
    should_fallback = score >= fallback_score or "low_quality_text" in issues

    return TextQualityReport(
        issues=issues,
        score=score,
        should_fallback=should_fallback,
        char_count=len(text),
        word_count=len(words),
        letter_count=letter_count,
        vi_diacritic_ratio=round(vi_ratio, 4),
        unaccented_signal_ratio=round(signal_ratio, 4),
        mojibake_count=mojibake_count,
        html_entity_count=html_entity_count,
        alphanumeric_artifact_ratio=round(alphanumeric_artifact_ratio, 4),
    )


def vietnamese_text_quality_issues(text: str, lang: str = "vi") -> list[str]:
    """Return quality issue names for backward-compatible tests and callers."""
    return analyze_vietnamese_text_quality(text, lang=lang).issues


def should_fallback_to_ocr(quality_issues: list[str], fallback_score: int = 3) -> bool:
    """Decide whether quality signals are strong enough to force rendered OCR."""
    if not quality_issues:
        return False

    issue_set = set(quality_issues)
    if "low_quality_text" in issue_set:
        return True

    score = sum(QUALITY_ISSUE_WEIGHTS.get(issue, 1) for issue in issue_set)
    return score >= fallback_score


# Backward-compatible private aliases
_is_low_quality_text = is_low_quality_text
_analyze_vietnamese_text_quality = analyze_vietnamese_text_quality
_vietnamese_text_quality_issues = vietnamese_text_quality_issues
_should_fallback_to_ocr = should_fallback_to_ocr

__all__ = [
    "is_low_quality_text",
    "analyze_vietnamese_text_quality",
    "vietnamese_text_quality_issues",
    "should_fallback_to_ocr",
    "_is_low_quality_text",
    "_analyze_vietnamese_text_quality",
    "_vietnamese_text_quality_issues",
    "_should_fallback_to_ocr",
]
