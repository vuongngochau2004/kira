"""Application constants."""

from enum import Enum


# =============================================================================
# ENUMS - Categorical constants
# =============================================================================

class HTTPStatus(int, Enum):
    """HTTP status codes."""

    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500


class DocumentStatus(str, Enum):
    """Document processing statuses."""

    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageRole(str, Enum):
    """Message roles in conversations."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class UserRole(str, Enum):
    """User roles in the system."""

    USER = "user"
    ADMIN = "admin"


# =============================================================================
# CONFIGURATION CONSTANTS - Numeric/string values
# =============================================================================

# Pagination
DEFAULT_LIMIT = 100
DEFAULT_OFFSET = 0
DEFAULT_CONVERSATION_LIMIT = 50

# LLM Defaults
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048
DEFAULT_LLM_TIMEOUT = 60.0

# Processing
DEFAULT_PROCESSING_TIMEOUT = 600

# RAG
MAX_CONTEXT_TOKENS = 4096
MIN_CONTEXT_LENGTH = 200
MIN_RETRIEVAL_SCORE = 0.70  # Minimum average score for context to be considered relevant
MIN_RETRIEVAL_DOCS = 1  # Minimum documents needed for sufficient context

# =============================================================================
# ERROR MESSAGES - User-facing text (ready for i18n)
# =============================================================================

ERR_DOC_NOT_FOUND = "Document not found"
ERR_CONVERSATION_NOT_FOUND = "Conversation not found"
ERR_PROCESSING_FAILED = "Processing failed"
ERR_NO_CONTENT = "No text content after cleaning"
ERR_NO_CHUNKS = "No chunks created"
ERR_EXTRACTION_FAILED = "Extraction failed"

__all__ = [
    # Enums
    "HTTPStatus",
    "DocumentStatus",
    "MessageRole",
    "UserRole",
    # Configuration Constants
    "DEFAULT_LIMIT",
    "DEFAULT_OFFSET",
    "DEFAULT_CONVERSATION_LIMIT",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_LLM_TIMEOUT",
    "DEFAULT_PROCESSING_TIMEOUT",
    "MAX_CONTEXT_TOKENS",
    "MIN_CONTEXT_LENGTH",
    "MIN_RETRIEVAL_SCORE",
    "MIN_RETRIEVAL_DOCS",
    # Error Messages
    "ERR_DOC_NOT_FOUND",
    "ERR_CONVERSATION_NOT_FOUND",
    "ERR_PROCESSING_FAILED",
    "ERR_NO_CONTENT",
    "ERR_NO_CHUNKS",
    "ERR_EXTRACTION_FAILED",
]
