"""Models module exports."""

from src.models.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    UserWithTokenResponse,
)
from src.models.documents import (
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
    ChunkResponse,
    ChunkWithScore,
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from src.models.evaluation import (
    EvaluationMetric,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    GoldenDataset,
    GoldenDatasetSample,
    EvaluationHistory,
)

__all__ = [
    # Auth
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "UserResponse",
    "UserWithTokenResponse",
    # Documents
    "DocumentCreate",
    "DocumentResponse",
    "DocumentListResponse",
    "ChunkResponse",
    "ChunkWithScore",
    "ConversationCreate",
    "ConversationResponse",
    "MessageCreate",
    "MessageResponse",
    # Evaluation
    "EvaluationMetric",
    "EvaluationRequest",
    "EvaluationResponse",
    "EvaluationResult",
    "BatchEvaluationRequest",
    "BatchEvaluationResponse",
    "GoldenDataset",
    "GoldenDatasetSample",
    "EvaluationHistory",
]
