"""Hexagonal Architecture Ports — External dependency contracts.

Ports define what the application NEEDS from the outside world.
Adapters (in shared/adapters/) provide the actual implementations.

Usage:
    # In application code — depend on ports only:
    from src.shared.ports import LLMPort, VectorStorePort

    # In server/main.py — wire concrete adapters to ports:
    from src.shared.adapters.llm.glm_adapter import GLMAdapter
    await container.register_singleton(LLMPort, GLMAdapter())
"""
from .llm import LLMPort
from .vector_store import VectorStorePort, VectorDocument, SearchResult
from .embedding import EmbeddingPort
from .storage import StoragePort
from .ocr import OCRPort

__all__ = [
    # Ports
    "LLMPort",
    "VectorStorePort",
    "EmbeddingPort",
    "StoragePort",
    "OCRPort",
    # Data classes (shared across ports and adapters)
    "VectorDocument",
    "SearchResult",
]
