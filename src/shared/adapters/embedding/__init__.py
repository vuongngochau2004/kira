"""Embedding adapters package."""

from .api_adapter import EmbeddingAPIAdapter
from .factory import create_embedding_adapter
from .ollama_adapter import OllamaEmbeddingAdapter
from .tei_adapter import TEIEmbeddingAdapter

__all__ = [
    "EmbeddingAPIAdapter",
    "OllamaEmbeddingAdapter",
    "TEIEmbeddingAdapter",
    "create_embedding_adapter",
]
