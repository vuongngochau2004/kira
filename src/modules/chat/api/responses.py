"""
Chat API response DTOs - Pydantic models for HTTP response formatting.

Extracted from src/models/chat.py into the chat module's API layer.
These DTOs decouple HTTP concerns from domain logic.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class ChatResponse(BaseModel):
    """Response DTO for chat endpoints.

    Attributes:
        content: Generated response text
        citations: Legacy flat list of citations (deprecated, use sources)
        sources: Grouped document sources (preferred format)
        citation_verification: Optional citation verification stats
        conversation_id: ID of the conversation
        message_id: ID of the assistant message
        metadata: Processing metadata (handler, latency, etc.)
    """

    content: str
    citations: List[dict] = Field(
        default_factory=list,
        description="Legacy flat list of citations (deprecated, use 'sources' instead)",
    )
    sources: List[dict] = Field(
        default_factory=list,
        description="Grouped document sources (preferred format)",
    )
    citation_verification: Optional[dict] = None
    conversation_id: str
    message_id: str
    metadata: dict


class ConversationResponse(BaseModel):
    """Response DTO for conversation endpoints.

    Attributes:
        id: Conversation UUID
        user_id: Owner user ID
        title: Conversation title
        message_count: Number of messages in conversation
        last_message_at: Timestamp of last message
        created_at: Creation timestamp
    """

    id: str
    user_id: str
    title: str
    message_count: int
    last_message_at: Optional[str] = None
    created_at: str


class ConversationDetailResponse(BaseModel):
    """Response DTO for conversation detail with messages.

    Attributes:
        id: Conversation UUID
        title: Conversation title
        message_count: Number of messages
        messages: List of message dicts
    """

    id: str
    title: str
    message_count: int
    messages: List[dict]


class MessageResponse(BaseModel):
    """Response DTO for individual messages.

    Attributes:
        id: Message UUID
        conversation_id: Parent conversation UUID
        role: Message role (user/assistant)
        content: Message content text
        sources: Grouped document sources with chunks
        citations: Legacy flat citations list (deprecated)
        thinking_data: Thinking/reasoning data from LLM
        created_at: Creation timestamp
    """

    id: str
    conversation_id: str
    role: str
    content: str
    sources: List[dict] = Field(
        default_factory=list,
        description="Grouped document sources with chunks",
    )
    citations: List[dict] = Field(
        default_factory=list,
        description="Legacy flat citations list (deprecated)",
    )
    thinking_data: dict = Field(default_factory=dict)
    created_at: str


__all__ = [
    "ChatResponse",
    "ConversationResponse",
    "ConversationDetailResponse",
    "MessageResponse",
]