"""FastAPI application entry point for K.I.R.A Simplified."""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.config import settings
from src.database.session import init_db, close_db
from src.indexing.qdrant_store import ensure_collection, get_client
from src.tools.retrieval_tools import init_retrieval_tools
from src.tools.ingestion_tools import init_ingestion_tools
from src.ingestion.embedding import preload_model
from src.api import auth, documents, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    await init_db()
    ensure_collection()
    preload_model()
    init_retrieval_tools(qdrant_store=get_client())
    init_ingestion_tools()
    yield
    await close_db()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="K.I.R.A Simplified - RAG with Hybrid Retrieval",
        version="1.0.0",
        lifespan=lifespan,
    )

    _setup_cors(app)
    _setup_exception_handlers(app)
    _setup_routes(app)
    _setup_health_checks(app)

    return app


def _setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _setup_exception_handlers(app: FastAPI) -> None:
    """Configure exception handlers."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        message = str(exc) if settings.debug else "Internal server error"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": message},
        )


def _setup_routes(app: FastAPI) -> None:
    """Configure API routes."""
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


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
        "src.main:app",
        host="0.0.0.0",
        port=8006,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
