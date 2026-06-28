"""Startup dependency checks with a concise Loguru report."""

import asyncio
import importlib.metadata
import importlib.util
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from loguru import logger

from src.config.config import settings
from src.shared.adapters.embedding import create_embedding_adapter
from src.shared.adapters.llm.glm_adapter import GLMAdapter
from src.shared.adapters.ocr.paddleocr_adapter import PaddleOCRAdapter
from src.shared.adapters.vector.qdrant_adapter import QdrantAdapter
from src.shared.infrastructure.llm.client import LLMClient
from src.modules.document.infrastructure.storage.storage import get_client as get_minio_client
from src.worker.celery_app import celery_app


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
        return ServiceHealth(name, "UP", result if isinstance(result, str) else "reachable", latency_ms)
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
    return await PaddleOCRAdapter().health_check()


async def log_startup_service_health(llm_client: LLMClient) -> list[ServiceHealth]:
    """Run non-database checks concurrently and emit their Loguru status report."""
    dependency_checks = await asyncio.gather(
        _check_service("Qdrant", QdrantAdapter().health_check),
        _check_service("MinIO", _check_minio),
        _check_service("Redis", _check_redis),
        _check_service("Celery worker", _check_celery_worker),
        _check_service("Embedding API", create_embedding_adapter().health_check),
        _check_service(f"LLM ({settings.llm_provider})", GLMAdapter(client=llm_client).health_check),
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
