"""
Chat API request DTOs - Pydantic models for HTTP request validation.

These DTOs decouple HTTP concerns from domain logic.
"""

from pydantic import BaseModel, Field


class ChatStreamRequest(BaseModel):
    """Request DTO for streaming chat endpoint.

    Attributes:
        message: User's query text
        conversation_id: Optional existing conversation ID
        evaluate: Whether to run DeepEval evaluation
        evaluation_metrics: Optional specific metrics to evaluate
    """

    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: str | None = None
    evaluate: bool = False
    evaluation_metrics: list[str] | None = None


class ChatCompletionRequest(BaseModel):
    """Request DTO for non-streaming chat completion endpoint.

    Attributes:
        message: User's query text
        conversation_id: Optional existing conversation ID
        temperature: Sampling temperature (0.0 - 1.0)
        max_tokens: Maximum tokens to generate
    """

    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: str | None = None
    temperature: float = Field(default=0.7, ge=0, le=1)
    max_tokens: int = Field(default=2048, ge=1, le=8192)


class ConversationCreate(BaseModel):
    """Request DTO for creating a conversation."""

    title: str | None = Field(default="Cuộc trò chuyện mới", max_length=255)


__all__ = ["ChatStreamRequest", "ChatCompletionRequest", "ConversationCreate"]
