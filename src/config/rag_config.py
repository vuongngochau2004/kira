"""RAG router configuration - keywords, thresholds, and confidence scores.

This module centralizes all RAG routing configuration for maintainability.
Senior Dev Notes:
- Keywords are organized by category for clarity
- Confidence scores use named enums (no magic numbers)
- Config is frozen (immutable) for thread-safety
"""

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Final


class Confidence(Enum):
    """Confidence scores for RAG routing decisions.

    Values represent certainty that query should use RAG (0.0-1.0).
    """
    HIGH = 0.95          # File/document indicators - very certain
    MEDIUM_HIGH = 0.7    # Document keyword matches - high certainty
    MEDIUM = 0.5         # Long substantive queries - moderate certainty
    LOW = 0.2            # Short/generic queries - low certainty (likely conversational)


class Thresholds(Enum):
    """Minimum thresholds for routing decisions."""
    DOC_INDICATOR_MIN_MATCH = 1  # Minimum keyword matches for medium-high confidence
    LONG_QUERY_MIN_WORDS = 4     # Minimum words for medium confidence


class RAGKeywords:
    """RAG routing keywords organized by category.

    All keywords are lowercase for case-insensitive matching.
    Keywords are pre-processed into frozensets for O(1) lookup performance.

    Performance: O(min(n, m)) where n=keywords, m=query words
    Memory: ~2KB for all keyword sets
    """

    # File/document indicators → highest confidence
    FILE: Final = frozenset({
        "file", "tài liệu", "tập tin", "doc", "docx", "pdf", "txt", "trích dẫn"
    })

    # General document indicators → medium-high confidence
    DOCUMENT: Final = frozenset({
        # Common research verbs
        "tìm", "kiểm tra", "tra cứu", "theo", "trong", "về", "liên quan",
        # Administrative terms
        "quy định", "thủ tục", "cách", "như thế nào", "làm sao",
        # ĐHBKĐN-specific keywords
        "điều", "điều kiện", "điều khoản",
        "xét", "tốt nghiệp",
        "học bạ", "tín chỉ",
        "tuyển sinh", "tuyển", "nhập học", "hồ sơ",
        "học phí", "mức học phí",
        "quy chế",
        "sinh viên", "đào tạo",
        "cơ cấu", "tổ chức",
        "nghiên cứu", "khoa học",
        "quản lý", "giảng dạy",
        "thực hiện", "hành chính",
    })

    @classmethod
    @lru_cache(maxsize=1)
    def get_all_keywords(cls) -> frozenset:
        """Get union of all keywords for debugging/validation."""
        return cls.FILE | cls.DOCUMENT


@dataclass(frozen=True)
class RAGConfig:
    """RAG router configuration with sensible defaults.

    This config is frozen (immutable) for thread-safety and to prevent
    accidental modification at runtime.

    Attributes:
        file_keywords: Frozenset of file/document indicator keywords
        doc_keywords: Frozenset of document-related keywords
        confidence_high: Confidence score for file indicators
        confidence_medium_high: Confidence score for doc keyword matches
        confidence_medium: Confidence score for long queries
        confidence_low: Default confidence for short queries
        doc_indicator_min_match: Minimum keyword matches for medium-high
        long_query_min_words: Minimum words for medium confidence
    """
    file_keywords: frozenset = RAGKeywords.FILE
    doc_keywords: frozenset = RAGKeywords.DOCUMENT

    confidence_high: float = Confidence.HIGH.value
    confidence_medium_high: float = Confidence.MEDIUM_HIGH.value
    confidence_medium: float = Confidence.MEDIUM.value
    confidence_low: float = Confidence.LOW.value

    doc_indicator_min_match: int = Thresholds.DOC_INDICATOR_MIN_MATCH.value
    long_query_min_words: int = Thresholds.LONG_QUERY_MIN_WORDS.value

    @classmethod
    @lru_cache(maxsize=1)
    def get_default(cls) -> "RAGConfig":
        """Get singleton default config (cached)."""
        return cls()


# Export public API
__all__ = [
    "Confidence",
    "Thresholds",
    "RAGKeywords",
    "RAGConfig",
]
