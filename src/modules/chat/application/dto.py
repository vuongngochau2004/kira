"""
Data Transfer Objects (DTOs) for the chat module.

Defines input/output boundaries between layers:
- ChatQuery: Input DTO for chat use cases
- ChatResult: Output DTO for non-streaming results
- StreamChunk: Output DTO for streaming chunks

These DTOs decouple the API layer from domain logic,
allowing each layer to evolve independently.
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.shared.ports.classification import Intent, ClassificationResult
from src.shared.ports.handlers import HandlerResult, Citation


@dataclass
class ChatQuery:
    """Input DTO for chat use cases.

    Encapsulates all data needed to process a chat query,
    decoupled from HTTP request concerns.

    Attributes:
        message: User's query text
        user_id: User identifier for personalization and scoping
        conversation_id: Optional existing conversation ID
        conversation_history: Optional prior messages for context
        context: Optional additional context dict
        evaluate: Whether to run RAGAS evaluation
        evaluation_metrics: Optional specific metrics to evaluate
    """

    message: str
    user_id: str | UUID
    conversation_id: UUID | None = None
    conversation_history: list[dict[str, str]] | None = None
    context: dict[str, Any] | None = None
    evaluate: bool = False
    evaluation_metrics: list[str] | None = None

    def __post_init__(self):
        """Validate ChatQuery fields after initialization."""
        if not self.message or not self.message.strip():
            raise ValueError("message cannot be empty")
        if len(self.message) > 5000:
            raise ValueError("message exceeds maximum length of 5000 characters")


@dataclass
class ChatResult:
    """Output DTO for non-streaming chat results.

    Decoupled from HandlerResult to allow API layer
    to add its own formatting (conversation_id, message_id).

    Attributes:
        content: Generated response text
        citations: Document citations supporting the response
        metadata: Processing metadata (handler, latency, etc.)
        conversation_id: ID of the conversation (if persisted)
        message_id: ID of the assistant message (if persisted)
        status: Result status (success, error)
        error: Error message if status is error
    """

    content: str = ""
    citations: list[Citation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    conversation_id: str | None = None
    message_id: str | None = None
    status: str = "success"
    error: str | None = None

    @classmethod
    def from_handler_result(
        cls,
        result: HandlerResult,
        classification: ClassificationResult,
        latency_ms: float = 0.0,
    ) -> "ChatResult":
        """Create ChatResult from a HandlerResult.

        Args:
            result: HandlerResult from handler execution
            classification: Classification result that determined routing
            latency_ms: Total processing latency in milliseconds

        Returns:
            ChatResult with converted data
        """
        return cls(
            content=result.content,
            citations=result.citations,
            metadata={
                **result.metadata,
                "classification": classification.to_dict(),
                "total_latency_ms": latency_ms,
            },
            status=result.status,
            error=result.error,
        )


@dataclass
class StreamChunk:
    """Output DTO for streaming chat chunks.

    Factory methods for creating common chunk types
    to ensure consistent formatting across the system.
    """

    type: str
    data: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def routing(
        router_name: str,
        intent: str,
        confidence: float,
        reasoning: str = "",
    ) -> dict[str, Any]:
        """Create a routing decision chunk.

        Args:
            router_name: Name of the selected handler
            intent: Classified intent string
            confidence: Classification confidence (0-1)
            reasoning: Classification reasoning

        Returns:
            Dict chunk with type='routing'
        """
        return {
            "type": "routing",
            "data": {
                "router": router_name,
                "intent": intent,
                "confidence": confidence,
                "reasoning": reasoning,
            },
        }

    @staticmethod
    def error(message: str) -> dict[str, Any]:
        """Create an error chunk.

        Args:
            message: Error message

        Returns:
            Dict chunk with type='error'
        """
        return {"type": "error", "data": {"error": message}}


__all__ = ["ChatQuery", "ChatResult", "StreamChunk"]