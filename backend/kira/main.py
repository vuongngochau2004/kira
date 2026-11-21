"""FastAPI application entry point for K.I.R.A Simplified."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from kira.admin.router import router as admin_router
from kira.auth.router import router as auth_router
from kira.chat.router import router as chat_router
from kira.config import settings
from kira.core.cors import setup_cors
from kira.core.errors import setup_exception_handlers
from kira.core.health import log_startup_service_health
from kira.core.logger import setup_logging
from kira.db.session import close_db, init_db
from kira.documents.router import router as documents_router
from kira.evaluation.router import router as evaluation_router
from kira.legal.router import router as legal_router
from kira.pipeline_lab.router import router as debug_router
from kira.providers.llm.client import LLMClient, LLMProvider
from kira.retrieval.rerank.service import init_reranking_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting {} dependency initialization", settings.app_name)
    await init_db()

    # Initialize LLM client for reranking
    llm_client = _create_llm_client()
    init_reranking_service(llm_client=llm_client)
    await log_startup_service_health(llm_client)

    yield
    logger.info("Shutting down {}", settings.app_name)
    await close_db()


def _create_llm_client() -> LLMClient:
    """Build the configured LLM client with its provider enum, not a raw string."""
    provider = LLMProvider(settings.llm_provider)
    model = None
    if provider is LLMProvider.GLM:
        model = settings.glm_model
    elif provider is LLMProvider.OPENAI_COMPATIBLE:
        model = settings.bk_llm_model
    elif provider is LLMProvider.OLLAMA:
        model = settings.ollama_model
    elif provider is LLMProvider.GEMINI:
        model = settings.gemini_model

    return LLMClient(
        provider=provider,
        model=model,
        temperature=0.1,  # Low temperature for consistent reranking
        max_tokens=512,
        timeout=30.0,
    )


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    # Initialize Loguru unified logging
    setup_logging(debug=settings.debug)

    app = FastAPI(
        title=settings.app_name,
        description="K.I.R.A Simplified - RAG with Hybrid Retrieval",
        version="1.0.0",
        lifespan=lifespan,
    )

    setup_cors(app)
    setup_exception_handlers(app)
    _setup_routes(app)
    _setup_health_checks(app)

    return app


def _setup_routes(app: FastAPI) -> None:
    """Configure API routes from new server structure."""
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
    app.include_router(evaluation_router, prefix="/api/v1/evaluation", tags=["evaluation"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(debug_router, prefix="/api/v1/admin/pipeline-lab", tags=["pipeline-lab"])
    if settings.legal_enabled:
        app.include_router(legal_router, prefix="/api/v1/legal", tags=["legal"])


def _setup_health_checks(app: FastAPI) -> None:
    """Configure health check endpoints."""

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "ok", "service": settings.app_name}

    @app.get("/health/ready")
    async def readiness_check() -> dict:
        return {"status": "ready"}

    @app.get("/health/live")
    async def liveness_check() -> dict:
        return {"status": "alive"}


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "kira.main:app",
        host=settings.api_host,
        port=settings.backend_port,
        reload=settings.debug,
        reload_dirs=["src"],
        log_level="debug" if settings.debug else "info",
    )
