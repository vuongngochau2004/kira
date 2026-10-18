from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.config.config import settings
from src.modules.legal.api import dependencies
from src.modules.legal.api.endpoints import router
from src.modules.legal.application.errors import LegalProvisionNotFound
from src.modules.legal.application.provision_history import GetProvisionHistory
from src.server import startup_health
from src.shared.infrastructure.auth.dependencies import get_current_user
from tests.legal_fakes import FakeProvisionSearch, make_hit

KEY = "31/2024/QH15#D3.K1"
OLD = make_hit(KEY, "cũ", date(2024, 8, 1), date(2026, 7, 1))
NEW = make_hit(KEY, "mới", date(2026, 7, 1))


async def test_history_lists_versions_and_version_in_force() -> None:
    history = await GetProvisionHistory(FakeProvisionSearch([NEW, OLD])).execute(
        KEY, date(2025, 1, 1)
    )
    assert [v.text for v in history.versions] == ["cũ", "mới"]
    assert history.in_force is not None and history.in_force.text == "cũ"
    assert (history.label, history.number) == ("Khoản 1", "31/2024/QH15")


async def test_unknown_provision_raises() -> None:
    with pytest.raises(LegalProvisionNotFound):
        await GetProvisionHistory(FakeProvisionSearch([])).execute(KEY, date(2025, 1, 1))


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/legal")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(), role="user", is_active=True
    )
    app.dependency_overrides[dependencies.get_provision_history_service] = lambda: (
        GetProvisionHistory(FakeProvisionSearch([OLD, NEW]))
    )
    return TestClient(app)


def test_endpoint_is_open_to_regular_users() -> None:
    response = _client().get("/api/v1/legal/provisions", params={"key": KEY, "date": "2026-08-01"})
    assert response.status_code == 200
    body = response.json()
    assert body["provision_key"] == KEY
    assert body["in_force"]["text"] == "mới"
    assert [v["valid_to"] for v in body["versions"]] == ["2026-07-01", None]


def test_endpoint_unknown_key_is_404() -> None:
    response = _client().get("/api/v1/legal/provisions", params={"key": "1/2000/QH10#D1"})
    assert response.status_code == 404


async def test_neo4j_health_is_skipped_when_legal_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "legal_enabled", False)
    health = await startup_health._check_service("Neo4j", startup_health._check_neo4j)
    assert health.state == "SKIP"


async def test_neo4j_health_reports_down(monkeypatch: pytest.MonkeyPatch) -> None:
    class DownGraph:
        async def health_check(self) -> bool:
            return False

        async def close(self) -> None:
            return None

    monkeypatch.setattr(settings, "legal_enabled", True)
    monkeypatch.setattr(
        startup_health.Neo4jLegalGraphAdapter, "from_settings", classmethod(lambda cls: DownGraph())
    )
    health = await startup_health._check_service("Neo4j", startup_health._check_neo4j)
    assert health.state == "DOWN"
