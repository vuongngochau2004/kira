"""Tests for startup dependency status reporting."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from kira.core import health as startup_health
from kira.core.health import _check_celery_worker, _check_service


@pytest.mark.asyncio
async def test_check_service_reports_up_with_detail() -> None:
    async def healthy() -> str:
        return "ready"

    result = await _check_service("Example", healthy)

    assert result.name == "Example"
    assert result.state == "UP"
    assert result.detail == "ready"
    assert result.latency_ms is not None


@pytest.mark.asyncio
async def test_check_service_reports_down_without_raising() -> None:
    async def unavailable() -> bool:
        return False

    result = await _check_service("Example", unavailable)

    assert result.state == "DOWN"
    assert result.detail == "health check returned false"


@pytest.mark.asyncio
async def test_celery_health_check_uses_its_own_short_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, float] = {}

    def ping(*, timeout: float) -> list[dict[str, str]]:
        observed["timeout"] = timeout
        return [{"worker@example": "pong"}]

    async def run_inline(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(startup_health.celery_app.control, "ping", ping)
    monkeypatch.setattr(startup_health.asyncio, "to_thread", run_inline)

    result = await _check_celery_worker()

    assert result == "1 worker(s) replied"
    assert observed["timeout"] == 1.0


@pytest.mark.asyncio
async def test_tei_health_reports_cloudflare_tunnel_failure() -> None:
    response = httpx.Response(503, text="<h1>Error 1033</h1>Cloudflare Tunnel error")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=response) as get:
        result = await _check_service(
            "Embedding API", lambda: startup_health._check_tei_health("embedding")
        )

    assert result.state == "DOWN"
    assert "HTTP 503" in result.detail
    assert "Cloudflare Tunnel error 1033" in result.detail
    assert get.await_args.args[0].endswith("/health/embedding")


@pytest.mark.asyncio
async def test_startup_report_includes_tei_reranker(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[str] = []

    async def fake_check_service(name, check):
        observed.append(name)
        return startup_health.ServiceHealth(name, "UP", "ready")

    monkeypatch.setattr(startup_health, "_check_service", fake_check_service)
    monkeypatch.setattr(startup_health.settings, "reranking_mode", "tei")

    await startup_health.log_startup_service_health(None)

    assert "Reranker (tei)" in observed
    assert "Embedding API" in observed


@pytest.mark.asyncio
async def test_admin_overview_includes_tei_reranker(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_check_service(name, check):
        return startup_health.ServiceHealth(name, "UP", "ready")

    monkeypatch.setattr(startup_health, "_check_service", fake_check_service)
    monkeypatch.setattr(startup_health.settings, "reranking_mode", "tei")

    overview = await startup_health.get_system_overview()

    assert {service["name"] for service in overview["services"]} >= {"Reranker (tei)"}
