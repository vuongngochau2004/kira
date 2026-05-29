"""Document-related schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentCreate(BaseModel):
    """Document upload metadata."""
    filename: str
    file_type: str
    file_size: int


class DocumentResponse(BaseModel):
    """Document response."""
    id: str
    user_id: str
    filename: str
    file_type: str
    file_size: int
    storage_path: str | None = None
    status: str
    error_message: str | None = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Document list response."""
    documents: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class ChunkResponse(BaseModel):
    """Document chunk response."""
    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int
    metadata: dict
    embedding_model: str

    class Config:
        from_attributes = True


class ChunkWithScore(ChunkResponse):
    """Chunk with retrieval score."""
    score: float
    text: str  # Alias for content


class ConversationCreate(BaseModel):
    """Create conversation request."""
    title: Optional[str] = Field(default="Cuộc trò chuyện mới", max_length=255)


class ConversationResponse(BaseModel):
    """Conversation response."""
    id: str
    user_id: str
    title: str
    message_count: int
    last_message_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Create message request."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class MessageResponse(BaseModel):
    """Message response."""
    id: str
    conversation_id: str
    role: str
    content: str
    sources: list
    token_count: int | None
    created_at: datetime

    class Config:
        from_attributes = True
