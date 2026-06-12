"""
Chat module - Core chat functionality.

Provides query routing, RAG, and conversational chat handling.
Uses handler-based architecture with CompositeClassifier for intent detection.

Architecture:
    application/  - Use cases, orchestration, DTOs
    domain/        - Domain services, business logic
    infrastructure/ - Handlers, LLM adapters
    api/           - Request/response DTOs

Import examples:
    from src.modules.chat import ChatUseCase, ChatQuery
    from src.modules.chat.infrastructure.handlers import RAGHandler
    from src.modules.chat.domain.services import RAGService
"""

# Application layer (use cases and DTOs) - lightweight, no heavy deps
from src.modules.chat.application import (
    ChatUseCase,
    ChatGraph,
    StreamingUseCase,
    ChatQuery,
    ChatResult,
    StreamChunk,
)

# Domain layer (services) - lightweight, no heavy deps
from src.modules.chat.domain.services import (
    RAGService,
    ConversationService,
)

# API layer (DTOs) - lightweight Pydantic models
from src.modules.chat.api import (
    ChatStreamRequest,
    ChatCompletionRequest,
    ChatResponse,
)

# Infrastructure layer (handlers) - lazy import to avoid circular deps
# These depend on heavy modules (agents, config, retrieval).
# Import them explicitly when needed:
#   from src.modules.chat.infrastructure.handlers import RAGHandler
#   from src.modules.chat.infrastructure.handlers import ConversationalHandler

__all__ = [
    # Application
    "ChatUseCase",
    "ChatGraph",
    "StreamingUseCase",
    "ChatQuery",
    "ChatResult",
    "StreamChunk",
    # Domain
    "RAGService",
    "ConversationService",
    # API
    "ChatStreamRequest",
    "ChatCompletionRequest",
    "ChatResponse",
]
