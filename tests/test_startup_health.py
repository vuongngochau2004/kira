"""Tests for startup dependency status reporting."""

import pytest

from src.server import startup_health
from src.server.startup_health import _check_celery_worker, _check_service


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
async def test_celery_health_check_uses_its_own_short_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, float] = {}

    def ping(*, timeout: float) -> list[dict[str, str]]:
        observed["timeout"] = timeout
        return [{"worker@example": "pong"}]

    monkeypatch.setattr(startup_health.celery_app.control, "ping", ping)

    result = await _check_celery_worker()

    assert result == "1 worker(s) replied"
    assert observed["timeout"] == 1.0
