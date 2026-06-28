"""Embedding adapters package."""
from .api_adapter import EmbeddingAPIAdapter
from .factory import create_embedding_adapter
from .ollama_adapter import OllamaEmbeddingAdapter

__all__ = ["EmbeddingAPIAdapter", "OllamaEmbeddingAdapter", "create_embedding_adapter"]
