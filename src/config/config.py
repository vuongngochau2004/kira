"""Application configuration using Pydantic Settings."""

from pathlib import Path

import yaml
from pydantic import Field, field_validator
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
            defaults = [
                "change-this-jwt-secret",
                "change-this-in-production",
                "secret",
                "your-jwt-secret-change-this",
            ]
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

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_value(cls, value):
        """Accept common DEBUG values from shells and process managers."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return value

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

    # ----- Redis / Celery -----
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_always_eager: bool = False
    celery_worker_concurrency: int = 2

    # ----- MinIO -----
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "kira_minio"
    minio_secret_key: str = "kira_minio_secret"
    minio_bucket: str = "kira-documents"
    minio_secure: bool = False

    # ----- JWT -----
    jwt_secret_key: str = Field(...)  # Required (loaded from JWT_SECRET_KEY env var)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_issuer: str = "kira-api"
    jwt_audience: str = "kira-clients"

    # ----- LLM Provider -----
    llm_provider: str = "glm"  # glm, gemini, openai_compatible, ollama

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

    # Ollama Cloud / OpenAI-compatible Ollama endpoint
    ollama_base_url: str = "https://ollama.com"
    ollama_api_keys: str = ""
    ollama_model: str = "gemma4:31b-cloud"

    # ----- Embedding (from settings.yaml) -----
    embedding_provider: str = "aivn"
    embedding_base_url: str = _static_config.get("embedding", {}).get(
        "base_url", "http://localhost:8888"
    )
    embedding_model: str = "vietnamese-embedding-v2"
    embedding_dim: int = _static_config.get("embedding", {}).get("dim", 1024)

    # ----- Retrieval (from settings.yaml) -----
    retrieval_k: int = _static_config.get("retrieval", {}).get("k", 5)
    rrf_k: int = _static_config.get("retrieval", {}).get("rrf_k", 60)
    retrieval_min_score_threshold: float = _static_config.get("retrieval", {}).get(
        "min_score_threshold", 0.65
    )

    # ----- Reranking (from settings.yaml) -----
    reranking_enabled: bool = _static_config.get("reranking", {}).get("enabled", False)
    reranking_mode: str = _static_config.get("reranking", {}).get("mode", "llm")
    reranking_top_k_before: int = _static_config.get("reranking", {}).get("top_k_before", 20)
    reranking_top_k_after: int = _static_config.get("reranking", {}).get("top_k_after", 5)
    reranking_min_score_threshold: float = _static_config.get("reranking", {}).get(
        "min_score_threshold", 0.3
    )
    reranking_timeout_ms: int = _static_config.get("reranking", {}).get("timeout_ms", 10000)

    # ----- Citations (from settings.yaml) -----
    max_citations: int = _static_config.get("citations", {}).get("max_citations", 10)
    min_score_threshold: float = _static_config.get("citations", {}).get("min_score_threshold", 0.3)
    snippet_length: int = _static_config.get("citations", {}).get("snippet_length", 900)

    # ----- Citation Verification (from settings.yaml) -----
    citation_verification_enabled: bool = _static_config.get("citation_verification", {}).get(
        "enabled", True
    )
    grounding_threshold: float = _static_config.get("citation_verification", {}).get(
        "grounding_threshold", 0.7
    )
    max_regenerate_attempts: int = _static_config.get("citation_verification", {}).get(
        "max_regenerate_attempts", 2
    )
    enable_warnings: bool = _static_config.get("citation_verification", {}).get(
        "enable_warnings", True
    )

    # ----- Chunking (from settings.yaml) -----
    chunk_size: int = _static_config.get("chunking", {}).get("size", 2048)
    chunk_overlap: int = _static_config.get("chunking", {}).get("overlap", 256)

    # ----- CORS -----
    cors_origins: str = Field(
        "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001,http://localhost:8006"
    )

    # ----- Auth -----
    auth_enabled: bool = Field(True)

    # ----- OCR (PaddleOCR) -----
    ocr_enabled: bool = Field(True)
    ocr_base_url: str = Field("")
    ocr_lang: str = Field("vi")  # vi, en, ch
    ocr_timeout: int = Field(30)  # seconds per request
    ocr_max_retries: int = Field(3)
    ocr_batch_size: int = Field(5)  # concurrent pages
    pdf_extractor: str = Field("vlm")  # vlm, docling, pymupdf
    docling_quality_gate_enabled: bool = Field(True)
    docling_quality_fallback_score: int = Field(3)
    pdf_render_dpi: int = Field(300)
    vlm_image_max_side: int = Field(2200)
    vlm_image_jpeg_quality: int = Field(88)
    vlm_transcription_timeout: int = Field(120)
    vlm_transcription_max_tokens: int = Field(4096)
    vlm_page_verification_enabled: bool = Field(True)
    vlm_verify_only_failed_pages: bool = Field(True)
    vlm_page_concurrency: int = Field(2)
    vlm_min_page_coverage_ratio: float = Field(0.7)
    document_audit_enabled: bool = Field(True)
    document_audit_dir: str = Field("reports/document_processing")
    legal_canonicalization_enabled: bool = Field(False)
    legal_canonicalization_max_chars: int = Field(60000)
    legal_chunking_enabled: bool = Field(True)

    # ----- Semantic Routing (from settings.yaml) -----
    semantic_routing_enabled: bool = Field(
        default=_static_config.get("semantic_routing", {}).get("enabled", True)
    )
    semantic_threshold: float = Field(
        default=_static_config.get("semantic_routing", {}).get("threshold", 0.75)
    )

    # ----- Classification fast-path config (from settings.yaml) -----
    classification_file_keywords: list[str] = Field(
        default=_static_config.get("classification", {}).get("file_keywords", [])
    )
    classification_drafting_actions: list[str] = Field(
        default=_static_config.get("classification", {}).get("drafting_actions", [])
    )
    classification_drafting_keywords: list[str] = Field(
        default=_static_config.get("classification", {}).get("drafting_keywords", [])
    )

    # ----- Query expansion (from settings.yaml) -----
    query_expansion_synonyms: dict[str, list[str]] = Field(
        default=_static_config.get("query_expansion", {}).get("synonyms", {})
    )

    # ----- Feature Flags (from settings.yaml) -----
    # Feature flags for gradual rollout of new architecture
    feature_flags: dict[str, bool | int] = Field(
        default=_static_config.get(
            "feature_flags",
            {
                "use_new_classification": False,  # Phase 02: New classification strategies
                "use_new_handlers": False,  # Phase 03: New handler architecture
                "enable_semantic_router": True,  # Semantic routing (existing)
                "enable_llmlite_provider": False,  # Experimental LLMlite provider
                "use_multi_agent_rag": False,  # Phase 04: Multi-Agent RAG architecture (custom orchestrator, 2026-06-11)
                "use_langgraph_rag": False,  # Phase 05: LangGraph-based RAG architecture (2026-06-11)
            },
        )
    )

    # ----- Evaluation -----
    evaluation_threshold: float = Field(
        default=_static_config.get("evaluation", {}).get("threshold", 0.7)
    )
    evaluation_report_dir: str = Field(
        default=_static_config.get("evaluation", {}).get("report_dir", "reports/evaluation")
    )

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
