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
STREAM_CHUNK_SIZE = 10

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


# =============================================================================
# BACKWARD COMPATIBILITY - Legacy constant names
# =============================================================================

# HTTP Status (legacy aliases)
HTTP_OK = HTTPStatus.OK
HTTP_CREATED = HTTPStatus.CREATED
HTTP_BAD_REQUEST = HTTPStatus.BAD_REQUEST
HTTP_UNAUTHORIZED = HTTPStatus.UNAUTHORIZED
HTTP_FORBIDDEN = HTTPStatus.FORBIDDEN
HTTP_NOT_FOUND = HTTPStatus.NOT_FOUND
HTTP_UNPROCESSABLE_ENTITY = HTTPStatus.UNPROCESSABLE_ENTITY
HTTP_INTERNAL_SERVER_ERROR = HTTPStatus.INTERNAL_SERVER_ERROR

# Document Status (legacy aliases)
DOC_STATUS_UPLOADING = DocumentStatus.UPLOADING.value
DOC_STATUS_PROCESSING = DocumentStatus.PROCESSING.value
DOC_STATUS_COMPLETED = DocumentStatus.COMPLETED.value
DOC_STATUS_FAILED = DocumentStatus.FAILED.value

# Message Role (legacy aliases)
ROLE_USER = MessageRole.USER.value
ROLE_ASSISTANT = MessageRole.ASSISTANT.value
ROLE_SYSTEM = MessageRole.SYSTEM.value

# User Role (legacy aliases)
USER_ROLE_USER = UserRole.USER.value
USER_ROLE_ADMIN = UserRole.ADMIN.value

__all__ = [
    # Enums
    "HTTPStatus",
    "DocumentStatus",
    "MessageRole",
    "UserRole",
    # Legacy HTTP Status (backward compatibility)
    "HTTP_OK",
    "HTTP_CREATED",
    "HTTP_BAD_REQUEST",
    "HTTP_UNAUTHORIZED",
    "HTTP_FORBIDDEN",
    "HTTP_NOT_FOUND",
    "HTTP_UNPROCESSABLE_ENTITY",
    "HTTP_INTERNAL_SERVER_ERROR",
    # Legacy Document Status (backward compatibility)
    "DOC_STATUS_UPLOADING",
    "DOC_STATUS_PROCESSING",
    "DOC_STATUS_COMPLETED",
    "DOC_STATUS_FAILED",
    # Legacy Message Role (backward compatibility)
    "ROLE_USER",
    "ROLE_ASSISTANT",
    "ROLE_SYSTEM",
    # Legacy User Role (backward compatibility)
    "USER_ROLE_USER",
    "USER_ROLE_ADMIN",
    # Configuration Constants
    "DEFAULT_LIMIT",
    "DEFAULT_OFFSET",
    "DEFAULT_CONVERSATION_LIMIT",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_LLM_TIMEOUT",
    "DEFAULT_PROCESSING_TIMEOUT",
    "STREAM_CHUNK_SIZE",
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
