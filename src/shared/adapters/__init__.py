"""Hexagonal Architecture Secondary Adapters.

Adapters implement the Ports defined in shared/ports/, wrapping
infrastructure components.
"""
from .llm.glm_adapter import GLMAdapter
from .vector.qdrant_adapter import QdrantAdapter
from .embedding.api_adapter import EmbeddingAPIAdapter
from .storage.minio_adapter import MinIOAdapter
from .ocr.paddleocr_adapter import PaddleOCRAdapter

__all__ = [
    "GLMAdapter",
    "QdrantAdapter",
    "EmbeddingAPIAdapter",
    "MinIOAdapter",
    "PaddleOCRAdapter",
]
