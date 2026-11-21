"""Tests for provider-selected embedding adapters."""

from kira.config import EmbeddingProvider, settings
from kira.providers.embedding.api import EmbeddingAPIAdapter
from kira.providers.embedding.factory import create_embedding_adapter
from kira.providers.embedding.ollama import OllamaEmbeddingAdapter
from kira.providers.embedding.tei import TEIEmbeddingAdapter


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


def test_factory_returns_tei_adapter_with_matching_settings(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", EmbeddingProvider.TEI)
    monkeypatch.setattr(settings, "tei_embedding_dim", 2048)

    adapter = create_embedding_adapter()

    assert isinstance(adapter, TEIEmbeddingAdapter)
    assert settings.embedding_base_url == settings.tei_base_url
    assert settings.embedding_model == settings.tei_embedding_model
    assert settings.embedding_dim == 2048
    assert settings.qdrant_vector_dim == adapter.dimension
