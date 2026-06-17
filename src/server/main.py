"""FastAPI application entry point for K.I.R.A Simplified."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.config import settings
from src.shared.infrastructure.persistence.database.session import init_db, close_db
from src.tools.retrieval_tools import init_retrieval_tools
from src.tools.ingestion_tools import init_ingestion_tools
from src.modules.retrieval.domain.services.reranking_service import init_reranking_service
from src.shared.adapters.embedding.api_adapter import EmbeddingAPIAdapter
from src.shared.infrastructure.llm.client import LLMClient
from src.modules.retrieval.domain.services.hybrid_search import set_llm_client
from src.modules.chat.api.endpoints import router as chat_router
from src.modules.document.api.endpoints import router as documents_router
from src.server.api.v1.auth.endpoints import router as auth_router
from src.server.api.v1.evaluation.endpoints import router as evaluation_router
from src.server.api.v1.metrics.endpoints import router as metrics_router
from src.server.api.v1.admin.endpoints import router as admin_router

from .api.middleware.cors_middleware import setup_cors
from .api.middleware.error_handler_middleware import setup_exception_handlers
from src.shared.infrastructure.monitoring import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    await init_db()
    await EmbeddingAPIAdapter().health_check()
    init_retrieval_tools()
    init_ingestion_tools()

    # Initialize LLM client for reranking
    llm_client = LLMClient(
        provider=settings.llm_provider,
        model=settings.glm_model if settings.llm_provider == "glm" else None,
        temperature=0.1,  # Low temperature for consistent reranking
        max_tokens=512,
        timeout=30.0,
    )
    init_reranking_service(llm_client=llm_client)
    set_llm_client(llm_client)

    yield
    await close_db()


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
    app.include_router(metrics_router, prefix="/api/v1/metrics", tags=["metrics"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])


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
        "src.server.main:app",
        host="0.0.0.0",
        port=8006,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
