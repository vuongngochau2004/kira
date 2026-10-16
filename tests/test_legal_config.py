import pytest

from src.config.config import Settings

_LEGAL_ENV = (
    "LEGAL_ENABLED",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "NEO4J_DATABASE",
    "LEGAL_QDRANT_COLLECTION",
    "LEGAL_AUTO_APPROVE_TYPES",
    "LEGAL_LLM_EXTRACTION_MAX_PROVISIONS",
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in _LEGAL_ENV:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_legal_settings_defaults(clean_env: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None, jwt_secret_key="test-secret")
    assert settings.legal_enabled is False
    assert settings.neo4j_uri == "bolt://localhost:7687"
    assert settings.neo4j_user == "neo4j"
    assert settings.neo4j_database == "neo4j"
    assert settings.legal_qdrant_collection == "legal_provisions"
    assert settings.legal_auto_approve_types == ["BASED_ON"]
    assert settings.legal_llm_extraction_max_provisions == 40


def test_legal_settings_from_environment(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("LEGAL_ENABLED", "true")
    clean_env.setenv("NEO4J_URI", "bolt://neo4j:7687")
    settings = Settings(_env_file=None, jwt_secret_key="test-secret")
    assert settings.legal_enabled is True
    assert settings.neo4j_uri == "bolt://neo4j:7687"
