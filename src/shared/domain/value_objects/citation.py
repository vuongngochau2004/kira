"""Citation Value Object — Source reference in RAG responses.

An immutable record of a retrieved document chunk used as a citation.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Citation:
    """Value Object: immutable citation from a retrieved document."""

    filename: str
    text: str
    page: int | None = None
    url: str | None = None
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if citation has confidence >= threshold."""
        return self.confidence >= threshold

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "filename": self.filename,
            "page": self.page,
            "text": self.text,
            "url": self.url,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


__all__ = ["Citation"]