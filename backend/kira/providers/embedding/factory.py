"""Embedding adapter factory."""

from kira.config import EmbeddingProvider, settings
from kira.providers.embedding.api import EmbeddingAPIAdapter
from kira.providers.embedding.base import EmbeddingPort
from kira.providers.embedding.ollama import OllamaEmbeddingAdapter
from kira.providers.embedding.tei import TEIEmbeddingAdapter


def create_embedding_adapter() -> EmbeddingPort:
    """Create the adapter selected by ``EMBEDDING_PROVIDER``."""
    if settings.embedding_provider is EmbeddingProvider.OLLAMA:
        return OllamaEmbeddingAdapter()
    if settings.embedding_provider is EmbeddingProvider.TEI:
        return TEIEmbeddingAdapter()
    return EmbeddingAPIAdapter()
