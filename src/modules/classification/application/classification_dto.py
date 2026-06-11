"""
Data Transfer Objects (DTOs) for classification use case.

Defines request/response models for classification operations.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.shared.kernel.interfaces.classification import ClassificationResult, Intent


@dataclass
class ClassifyQuery:
    """
    Query classification request DTO.

    Attributes:
        query: User query string to classify
        user_id: User ID making the query
        context: Additional context (conversation history, etc.)
    """

    query: str
    user_id: str | UUID
    context: dict[str, Any] | None = None

    def __post_init__(self):
        """Validate query after initialization."""
        if not self.query or not self.query.strip():
            raise ValueError("Query cannot be empty")

        # Normalize user_id to string
        if isinstance(self.user_id, UUID):
            object.__setattr__(self, "user_id", str(self.user_id))

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dict with query data
        """
        return {
            "query": self.query,
            "user_id": str(self.user_id),
            "context": self.context or {}
        }


@dataclass
class ClassificationResultDTO:
    """
    Classification result response DTO.

    Wraps ClassificationResult from kernel interfaces with additional metadata.

    Attributes:
        intent: Detected intent (RAG, CONVERSATIONAL, etc.)
        confidence: Classification confidence (0.0 to 1.0)
        reason: Human-readable explanation
        metadata: Additional metadata
        handler_hint: Suggested handler for this intent
    """

    intent: Intent
    confidence: float
    reason: str
    metadata: dict[str, Any]
    handler_hint: str | None = None

    @classmethod
    def from_classification_result(cls, result: ClassificationResult) -> "ClassificationResultDTO":
        """
        Create DTO from ClassificationResult.

        Args:
            result: ClassificationResult from kernel interfaces

        Returns:
            ClassificationResultDTO
        """
        return cls(
            intent=result.intent,
            confidence=result.confidence,
            reason=result.reason,
            metadata=result.metadata,
            handler_hint=result.handler_hint
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dict with result data
        """
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "metadata": self.metadata,
            "handler_hint": self.handler_hint
        }

    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """
        Check if result has high confidence.

        Args:
            threshold: Confidence threshold (default: 0.7)

        Returns:
            True if confidence >= threshold
        """
        return self.confidence >= threshold

    def is_rag_intent(self) -> bool:
        """Check if intent is RAG."""
        return self.intent == Intent.RAG

    def is_conversational_intent(self) -> bool:
        """Check if intent is CONVERSATIONAL."""
        return self.intent == Intent.CONVERSATIONAL
