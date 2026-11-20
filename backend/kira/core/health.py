"""Startup dependency checks with a concise Loguru report."""

import asyncio
import importlib.metadata
import importlib.util
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

from kira.config import EmbeddingProvider, RerankingMode, settings
from kira.legal.graph.neo4j import Neo4jLegalGraphAdapter
from kira.providers.embedding.factory import create_embedding_adapter
from kira.providers.llm.client import LLMClient
from kira.providers.ocr import PaddleOCR
from kira.providers.storage import get_client as get_minio_client
from kira.providers.vector_store import QdrantVectorStore
from kira.worker import celery_app


@dataclass(frozen=True)
class ServiceHealth:
    """Outcome of one startup dependency check."""

    name: str
    state: str
    detail: str
    latency_ms: float | None = None


async def _check_service(
    name: str,
    check: Callable[[], Awaitable[bool | str | ServiceHealth]],
) -> ServiceHealth:
    started_at = time.perf_counter()
    try:
        result = await asyncio.wait_for(check(), timeout=settings.service_health_timeout_seconds)
        latency_ms = (time.perf_counter() - started_at) * 1000
        if isinstance(result, ServiceHealth):
            return ServiceHealth(result.name, result.state, result.detail, latency_ms)
        if result is False:
            return ServiceHealth(name, "DOWN", "health check returned false", latency_ms)
        return ServiceHealth(
            name, "UP", result if isinstance(result, str) else "reachable", latency_ms
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000
        return ServiceHealth(name, "DOWN", f"{type(exc).__name__}: {exc}", latency_ms)


async def _check_minio() -> bool:
    return await asyncio.to_thread(lambda: get_minio_client().bucket_exists(settings.minio_bucket))


async def _check_redis() -> bool:
    def ping() -> bool:
        from redis import Redis

        client = Redis.from_url(
            settings.celery_broker_url,
            socket_connect_timeout=settings.service_health_timeout_seconds,
            socket_timeout=settings.service_health_timeout_seconds,
        )
        try:
            return bool(client.ping())
        finally:
            client.close()

    return await asyncio.to_thread(ping)


async def _check_celery_worker() -> str | bool:
    timeout = min(
        settings.celery_health_timeout_seconds,
        max(0.1, settings.service_health_timeout_seconds - 0.5),
    )
    replies = await asyncio.to_thread(
        celery_app.control.ping,
        timeout=timeout,
    )
    if not replies:
        return False
    return f"{len(replies)} worker(s) replied"


async def _check_docling() -> str | bool:
    if importlib.util.find_spec("docling") is None:
        return False
    return f"version {importlib.metadata.version('docling')}"


async def _check_ocr() -> bool | ServiceHealth:
    if not settings.ocr_enabled:
        return ServiceHealth("PaddleOCR", "SKIP", "disabled")
    if not settings.ocr_base_url:
        return ServiceHealth("PaddleOCR", "SKIP", "not configured")
    return await PaddleOCR().health_check()


async def _check_tei_health(model: str) -> str:
    """Probe a specific DUT AI model and retain useful HTTP failure details."""
    url = f"{settings.tei_base_url.rstrip('/')}/health/{model}"
    headers = {"Authorization": f"Bearer {settings.tei_api_key}"} if settings.tei_api_key else {}
    timeout = max(0.1, settings.service_health_timeout_seconds - 0.5)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers)
    if response.status_code != 200:
        tunnel_error = " (Cloudflare Tunnel error 1033)" if "Error 1033" in response.text else ""
        raise RuntimeError(f"{model} health: HTTP {response.status_code}{tunnel_error}")
    return "HTTP 200"


async def _check_embedding() -> bool | str:
    """Check the selected embedding provider's model endpoint."""
    if settings.embedding_provider is EmbeddingProvider.TEI:
        return await _check_tei_health("embedding")
    return await create_embedding_adapter().health_check()


async def _check_reranker(llm_client: LLMClient | None) -> bool | str:
    """Check the configured reranking adapter."""
    if settings.reranking_mode == RerankingMode.TEI:
        return await _check_tei_health("rerank")
    if llm_client is None:
        raise RuntimeError("LLM reranker client is unavailable")
    return await (llm_client or LLMClient()).health_check()


async def _check_neo4j() -> bool | str | ServiceHealth:
    if not settings.legal_enabled:
        return ServiceHealth("Neo4j", "SKIP", "LEGAL_ENABLED=false")
    graph = Neo4jLegalGraphAdapter.from_settings()
    try:
        return "bolt reachable" if await graph.health_check() else False
    finally:
        await graph.close()


async def log_startup_service_health(llm_client: LLMClient) -> list[ServiceHealth]:
    """Run non-database checks concurrently and emit their Loguru status report."""
    dependency_checks = await asyncio.gather(
        _check_service("Qdrant", QdrantVectorStore().health_check),
        _check_service("Neo4j", _check_neo4j),
        _check_service("MinIO", _check_minio),
        _check_service("Redis", _check_redis),
        _check_service("Celery worker", _check_celery_worker),
        _check_service("Embedding API", _check_embedding),
        _check_service(
            f"Reranker ({settings.reranking_mode})",
            lambda: _check_reranker(llm_client),
        ),
        _check_service(f"LLM ({settings.llm_provider})", (llm_client or LLMClient()).health_check),
        _check_service("PaddleOCR", _check_ocr),
        _check_service("Docling", _check_docling),
    )
    checks = [ServiceHealth("PostgreSQL", "UP", "schema initialized"), *dependency_checks]

    logger.info("Startup dependency health report:")
    for check in checks:
        latency = f" in {check.latency_ms:.0f} ms" if check.latency_ms is not None else ""
        message = f"{check.name:<15} {check.state:<4} {check.detail}{latency}"
        if check.state in {"UP", "SKIP"}:
            logger.info(message)
        else:
            logger.warning(message)

    return checks


async def get_system_overview(llm_client: LLMClient | None = None) -> dict[str, Any]:
    """Collect system health and return dictionary matching the frontend AdminOverview schema."""
    dependency_checks = await asyncio.gather(
        _check_service("Qdrant", QdrantVectorStore().health_check),
        _check_service("Neo4j", _check_neo4j),
        _check_service("MinIO", _check_minio),
        _check_service("Redis", _check_redis),
        _check_service("Celery worker", _check_celery_worker),
        _check_service("Embedding API", _check_embedding),
        _check_service(
            f"Reranker ({settings.reranking_mode})",
            lambda: _check_reranker(llm_client),
        ),
        _check_service("PaddleOCR", _check_ocr),
        _check_service("Docling", _check_docling),
    )
    checks = [ServiceHealth("PostgreSQL", "UP", "schema initialized"), *dependency_checks]
    if llm_client is not None:
        llm_check = await _check_service(
            f"LLM ({settings.llm_provider})", (llm_client or LLMClient()).health_check
        )
        checks.append(llm_check)

    services: list[dict[str, str]] = []
    has_critical_error = False
    has_any_error = False

    for c in checks:
        if c.state == "UP":
            service_status = "ok"
        elif c.state == "SKIP":
            service_status = "configured"
        else:
            service_status = "error"
            has_any_error = True
            if c.name in {"PostgreSQL", "Redis", "Qdrant", "MinIO"}:
                has_critical_error = True

        services.append(
            {
                "name": c.name,
                "status": service_status,
                "detail": c.detail,
            }
        )

    if has_critical_error:
        overall_status = "error"
    elif has_any_error:
        overall_status = "degraded"
    else:
        overall_status = "ok"

    return {
        "status": overall_status,
        "services": services,
    }
