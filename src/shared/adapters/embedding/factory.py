"""Embedding adapter factory."""

from src.config.config import EmbeddingProvider, settings
from src.shared.adapters.embedding.api_adapter import EmbeddingAPIAdapter
from src.shared.adapters.embedding.ollama_adapter import OllamaEmbeddingAdapter
from src.shared.ports.embedding import EmbeddingPort


def create_embedding_adapter() -> EmbeddingPort:
    """Create the adapter selected by ``EMBEDDING_PROVIDER``."""
    if settings.embedding_provider is EmbeddingProvider.OLLAMA:
        return OllamaEmbeddingAdapter()
    return EmbeddingAPIAdapter()
