"""Tests for provider-selected embedding adapters."""

from src.config.config import EmbeddingProvider, settings
from src.shared.adapters.embedding.api_adapter import EmbeddingAPIAdapter
from src.shared.adapters.embedding.factory import create_embedding_adapter
from src.shared.adapters.embedding.ollama_adapter import OllamaEmbeddingAdapter


def test_factory_returns_aivn_adapter(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", EmbeddingProvider.AIVN)

    adapter = create_embedding_adapter()

    assert isinstance(adapter, EmbeddingAPIAdapter)
    assert settings.embedding_dim == 1024
    assert settings.qdrant_collection == settings.aivn_qdrant_collection


def test_factory_returns_ollama_adapter(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", EmbeddingProvider.OLLAMA)

    adapter = create_embedding_adapter()

    assert isinstance(adapter, OllamaEmbeddingAdapter)
    assert settings.embedding_dim == 768
    assert settings.qdrant_collection == settings.ollama_qdrant_collection
