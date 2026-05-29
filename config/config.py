"""Application configuration using Pydantic Settings."""

from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Load static config from YAML
_settings_path = Path(__file__).parent / "settings.yaml"
with open(_settings_path, "r", encoding="utf-8") as f:
    _static_config = yaml.safe_load(f) or {}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fail-fast on production with default secrets
        if self.app_env == "production":
            defaults = ["change-this-jwt-secret", "change-this-in-production", "secret", "your-jwt-secret-change-this"]
            if any(self.jwt_secret_key == d for d in defaults):
                raise ValueError(
                    "PRODUCTION ENVIRONMENT DETECTED WITH DEFAULT JWT SECRET! "
                    "Set JWT_SECRET_KEY environment variable."
                )

    # ----- Application -----
    app_name: str = "kira-simple"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-this-in-production"

    # ----- Database -----
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_user: str = "kira"
    postgres_password: str = "kira_secret"
    postgres_db: str = "kira_dev"

    # Database pool configuration
    db_pool_size: int = 20
    db_max_overflow: int = 40  # Increased for RAG workload
    db_pool_recycle: int = 3600

    # ----- Qdrant -----
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = _static_config.get("qdrant", {}).get("collection", "document_chunks")
    qdrant_vector_dim: int = _static_config.get("qdrant", {}).get("vector_dim", 1024)

    # ----- MinIO -----
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "kira_minio"
    minio_secret_key: str = "kira_minio_secret"
    minio_bucket: str = "kira-documents"
    minio_secure: bool = False

    # ----- JWT -----
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")  # Required
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_issuer: str = "kira-api"
    jwt_audience: str = "kira-clients"

    # ----- LLM Provider -----
    llm_provider: str = "glm"  # glm, gemini, openai

    # Z.ai GLM (Anthropic-compatible, default for Vietnamese)
    glm_api_url: str = "https://api.z.ai/api/anthropic"
    glm_api_key: str = ""
    glm_model: str = "glm-4.5"

    # BK Self-hosted LLM (OpenAI-compatible)
    bk_llm_base_url: str = ""
    bk_llm_model: str = ""
    bk_api_key: str = ""

    # Google Gemini (backup)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # OpenAI (optional)
    openai_api_key: str = ""

    # ----- Embedding (from settings.yaml) -----
    embedding_provider: str = "aivn"
    embedding_base_url: str = _static_config.get("embedding", {}).get("base_url", "http://localhost:8888")
    embedding_model: str = "vietnamese-embedding-v2"
    embedding_dim: int = _static_config.get("embedding", {}).get("dim", 1024)

    # ----- Retrieval (from settings.yaml) -----
    retrieval_k: int = _static_config.get("retrieval", {}).get("k", 5)
    rrf_k: int = _static_config.get("retrieval", {}).get("rrf_k", 60)

    # ----- Chunking (from settings.yaml) -----
    chunk_size: int = _static_config.get("chunking", {}).get("size", 2048)
    chunk_overlap: int = _static_config.get("chunking", {}).get("overlap", 256)

    # ----- CORS -----
    cors_origins: str = Field(
        "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001,http://localhost:8006",
        env="CORS_ORIGINS"
    )

    # ----- Auth -----
    auth_enabled: bool = Field(True, env="AUTH_ENABLED")

    # ----- OCR (PaddleOCR) -----
    ocr_enabled: bool = Field(True, env="OCR_ENABLED")
    ocr_base_url: str = Field("", env="OCR_BASE_URL")
    ocr_lang: str = Field("vi", env="OCR_LANG")  # vi, en, ch
    ocr_timeout: int = Field(30, env="OCR_TIMEOUT")  # seconds per request
    ocr_max_retries: int = Field(3, env="OCR_MAX_RETRIES")
    ocr_batch_size: int = Field(5, env="OCR_BATCH_SIZE")  # concurrent pages

    @property
    def database_url(self) -> str:
        """Async PostgreSQL connection URL."""
        import urllib.parse
        user = urllib.parse.quote_plus(self.postgres_user)
        password = urllib.parse.quote_plus(self.postgres_password)
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync PostgreSQL connection URL (for Alembic)."""
        import urllib.parse
        user = urllib.parse.quote_plus(self.postgres_user)
        password = urllib.parse.quote_plus(self.postgres_password)
        return (
            f"postgresql://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
