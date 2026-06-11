"""FastAPI application entry point for K.I.R.A Simplified."""

from contextlib import asynccontextmanager
import importlib.util
from pathlib import Path

from fastapi import FastAPI

from src.config.config import settings
from src.shared.infrastructure.persistence.database.session import init_db, close_db
from src.modules.retrieval.infrastructure.vector.qdrant_store import ensure_collection, get_client
from src.tools.retrieval_tools import init_retrieval_tools
from src.tools.ingestion_tools import init_ingestion_tools
from src.tools.reranking_tools import init_reranking_tools
from src.modules.document.domain.services.embedder import preload_model
from src.shared.infrastructure.llm.client import LLMClient
from src.modules.retrieval.domain.services.hybrid_search import set_llm_client

# Import from server/api structure (relative to src/server/)
from .api.v1.auth.endpoints import router as auth_router

# Dynamic imports for modules with hyphens in filenames
def load_module_from_file(module_name: str, file_path: Path | str):
    """Load a Python module from a file path (handles hyphens in filenames)."""
    file_path_str = str(file_path) if isinstance(file_path, Path) else file_path
    spec = importlib.util.spec_from_file_location(module_name, file_path_str)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {file_path_str}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load endpoint modules with hyphens
_server_path = Path(__file__).parent
auth_router = load_module_from_file("auth_endpoints", _server_path / "api" / "v1" / "auth" / "endpoints.py").router
documents_router = load_module_from_file("document_endpoints", _server_path / "api" / "v1" / "documents" / "document_endpoints.py").router
chat_router = load_module_from_file("chat_endpoints", _server_path / "api" / "v1" / "chat" / "chat_endpoints.py").router
evaluation_router = load_module_from_file("evaluation_endpoints", _server_path / "api" / "v1" / "evaluation" / "evaluation_endpoints.py").router
metrics_router = load_module_from_file("metrics_endpoints", _server_path / "api" / "v1" / "metrics" / "metrics_endpoints.py").router

from .api.middleware.cors_middleware import setup_cors
from .api.middleware.error_handler_middleware import setup_exception_handlers
from src.shared.infrastructure.monitoring import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    await init_db()
    ensure_collection()
    preload_model()
    init_retrieval_tools(qdrant_store=get_client())
    init_ingestion_tools()

    # Initialize LLM client for reranking
    llm_client = LLMClient(
        provider=settings.llm_provider,
        model=settings.glm_model if settings.llm_provider == "glm" else None,
        temperature=0.1,  # Low temperature for consistent reranking
        max_tokens=512,
        timeout=30.0,
    )
    init_reranking_tools(llm_client=llm_client)
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
