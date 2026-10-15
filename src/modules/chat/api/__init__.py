"""
Chat module API layer - Request and response DTOs.

Pydantic models for HTTP request validation and response formatting.
Decouples HTTP concerns from domain logic.
"""

from src.modules.chat.api.requests import (
    ChatCompletionRequest,
    ChatStreamRequest,
)
from src.modules.chat.api.responses import (
    ChatResponse,
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
)

__all__ = [
    "ChatStreamRequest",
    "ChatCompletionRequest",
    "ChatResponse",
    "ConversationResponse",
    "ConversationDetailResponse",
    "MessageResponse",
]
