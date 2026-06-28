"""Tests for startup LLM client configuration."""

from src.server.main import _create_llm_client
from src.shared.infrastructure.llm.client import LLMProvider


def test_startup_llm_client_uses_provider_enum(monkeypatch) -> None:
    monkeypatch.setattr("src.server.main.settings.llm_provider", "ollama")

    client = _create_llm_client()

    assert client.provider is LLMProvider.OLLAMA
