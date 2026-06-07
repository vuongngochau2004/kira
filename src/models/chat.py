"""Chat-related schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    """Chat request."""
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0, le=1)
    max_tokens: int = Field(default=2048, ge=1, le=8192)


class ChatResponse(BaseModel):
    """Chat response with grouped document structure."""
    content: str
    citations: List[dict] = Field(
        default_factory=list,
        description="Legacy flat list of citations (deprecated, use 'sources' instead)"
    )
    sources: List[dict] = Field(
        default_factory=list,
        description="Grouped document sources (preferred format)"
    )
    citation_verification: Optional[dict] = None  # Citation verification stats
    conversation_id: str
    message_id: str
    metadata: dict


class ConversationCreate(BaseModel):
    """Create conversation request."""
    title: Optional[str] = Field(default="Cuộc trò chuyện mới", max_length=255)


class ConversationResponse(BaseModel):
    """Conversation response."""
    id: str
    user_id: str
    title: str
    message_count: int
    last_message_at: Optional[str]
    created_at: str


class MessageResponse(BaseModel):
    """Message response with grouped document structure."""
    id: str
    conversation_id: str
    role: str
    content: str
    sources: List[dict] = Field(
        default_factory=list,
        description="Grouped document sources with chunks"
    )
    citations: List[dict] = Field(
        default_factory=list,
        description="Legacy flat citations list (deprecated)"
    )
    thinking_data: dict = Field(default_factory=dict)
    created_at: str
