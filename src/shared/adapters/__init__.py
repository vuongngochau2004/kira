"""Hexagonal Architecture Secondary Adapters.

Adapters implement the Ports defined in shared/ports/, wrapping
infrastructure components.
"""

from .embedding.api_adapter import EmbeddingAPIAdapter
from .llm.glm_adapter import GLMAdapter
from .ocr.paddleocr_adapter import PaddleOCRAdapter
from .storage.minio_adapter import MinIOAdapter
from .vector.qdrant_adapter import QdrantAdapter

__all__ = [
    "GLMAdapter",
    "QdrantAdapter",
    "EmbeddingAPIAdapter",
    "MinIOAdapter",
    "PaddleOCRAdapter",
]
