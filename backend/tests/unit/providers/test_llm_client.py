"""Tests for startup LLM client configuration."""

from kira.main import _create_llm_client
from kira.providers.llm.client import LLMProvider


def test_startup_llm_client_uses_provider_enum(monkeypatch) -> None:
    monkeypatch.setattr("kira.main.settings.llm_provider", "ollama")
    monkeypatch.setattr("kira.main.settings.ollama_model", "test-ollama")

    client = _create_llm_client()

    assert client.provider is LLMProvider.OLLAMA
    assert client.model == "test-ollama"


def test_startup_llm_client_openai_compatible(monkeypatch) -> None:
    monkeypatch.setattr("kira.main.settings.llm_provider", "openai_compatible")
    monkeypatch.setattr("kira.main.settings.bk_llm_model", "ggml-org/gemma-4-e4b-it-GGUF:Q4_0")

    client = _create_llm_client()

    assert client.provider is LLMProvider.OPENAI_COMPATIBLE
    assert client.model == "ggml-org/gemma-4-e4b-it-GGUF:Q4_0"
