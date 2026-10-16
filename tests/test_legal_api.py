from datetime import date
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.legal.api import dependencies
from src.modules.legal.api.endpoints import router
from src.modules.legal.application.delete_document import DeleteLegalDocument
from src.modules.legal.application.queries import LegalDocumentQueries
from src.modules.legal.application.records import CandidateStatus, LegalDocumentStatus
from src.modules.legal.application.review_relation import ReviewRelationCandidate
from src.modules.legal.application.upload_document import UploadLegalDocument
from src.modules.legal.domain.models import RelationType
from src.shared.infrastructure.auth.dependencies import get_current_user
from src.shared.infrastructure.persistence.database.session import get_session
from tests.legal_fakes import FakeStorage, InMemoryLegalRepository, make_candidate, make_document

LAW_TEXT = "Điều 1. Phạm vi điều chỉnh\nLuật này quy định về đất đai.".encode()


class FakeSession:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def commit(self) -> None:
        self.events.append("commit")


class FakeEnqueuer:
    def __init__(self, events: list[str], fail: bool = False) -> None:
        self.events = events
        self.fail = fail
        self.processed: list[UUID] = []
        self.published: list[UUID] = []

    def process(self, document_id: UUID) -> str:
        if self.fail:
            raise ConnectionError("redis down")
        self.events.append("enqueue")
        self.processed.append(document_id)
        return "task-process"

    def publish(self, document_id: UUID) -> str:
        self.events.append("enqueue")
        self.published.append(document_id)
        return "task-publish"


class Harness:
    def __init__(self, role: str = "admin") -> None:
        self.repository = InMemoryLegalRepository()
        self.storage = FakeStorage()
        self.events: list[str] = []
        self.enqueuer = FakeEnqueuer(self.events)
        self.user = SimpleNamespace(id=uuid4(), role=role, is_active=True)
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/legal")

        async def session_override():
            yield FakeSession(self.events)

        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_session] = session_override
        app.dependency_overrides[dependencies.get_upload_service] = lambda: UploadLegalDocument(
            self.repository, self.storage
        )
        app.dependency_overrides[dependencies.get_review_service] = lambda: ReviewRelationCandidate(
            self.repository
        )
        app.dependency_overrides[dependencies.get_queries] = lambda: LegalDocumentQueries(
            self.repository
        )
        app.dependency_overrides[dependencies.get_delete_service] = lambda: DeleteLegalDocument(
            self.repository, self.storage
        )
        app.dependency_overrides[dependencies.get_task_enqueuer] = lambda: self.enqueuer
        self.client = TestClient(app)


def _upload(harness: Harness, number: str = "31/2024/QH15", content: bytes = LAW_TEXT):
    return harness.client.post(
        "/api/v1/legal/documents",
        data={
            "number": number,
            "doc_type": "law",
            "title": "Luật Đất đai",
            "issuer": "Quốc hội",
            "issued_date": "2024-01-18",
            "effective_date": "2024-08-01",
        },
        files={"file": ("luat.txt", content, "text/plain")},
    )


def test_upload_creates_document_and_enqueues_processing() -> None:
    harness = Harness()
    response = _upload(harness)
    assert response.status_code == 201
    body = response.json()
    assert body["number"] == "31/2024/QH15"
    assert body["status"] == "uploaded"
    assert body["effective_date"] == "2024-08-01"
    assert harness.enqueuer.processed == [UUID(body["id"])]


def test_upload_commits_before_enqueue() -> None:
    harness = Harness()
    _upload(harness)
    assert harness.events == ["commit", "enqueue"]


def test_upload_errors_are_mapped() -> None:
    harness = Harness()
    assert _upload(harness).status_code == 201
    assert _upload(harness).status_code == 409
    assert _upload(harness, number="không hợp lệ", content=b"x").status_code == 422


def test_upload_reports_queue_failure() -> None:
    harness = Harness()
    harness.enqueuer.fail = True
    assert _upload(harness).status_code == 503


def test_non_admin_is_forbidden() -> None:
    harness = Harness(role="user")
    assert _upload(harness).status_code == 403
    assert harness.client.get("/api/v1/legal/documents").status_code == 403


async def _seed(harness: Harness):
    base = make_document("31/2024/QH15")
    amending = make_document(
        "99/2026/QH15",
        status=LegalDocumentStatus.PUBLISHED,
        effective_date=date(2026, 7, 1),
        text="Điều 1. Sửa đổi\nNội dung.",
    )
    await harness.repository.create_document(base)
    await harness.repository.create_document(amending)
    candidate = make_candidate(
        amending,
        RelationType.AMENDS,
        "31/2024/QH15",
        ref="D1",
        new_text="Điều 1. Mới.",
        status=CandidateStatus.PENDING,
    )
    await harness.repository.save_candidate(candidate)
    return base, amending, candidate


async def test_list_get_and_candidates() -> None:
    harness = Harness()
    base, amending, candidate = await _seed(harness)

    listed = harness.client.get("/api/v1/legal/documents", params={"status": "published"})
    assert listed.status_code == 200
    assert {d["number"] for d in listed.json()} == {"31/2024/QH15", "99/2026/QH15"}

    detail = harness.client.get(f"/api/v1/legal/documents/{amending.id}")
    assert detail.json()["provision_count"] == 1

    candidates = harness.client.get(f"/api/v1/legal/documents/{amending.id}/candidates")
    assert [c["id"] for c in candidates.json()] == [str(candidate.id)]
    assert candidates.json()[0]["target_provision_ref"] == "D1"

    assert harness.client.get(f"/api/v1/legal/documents/{uuid4()}").status_code == 404


async def test_approve_on_published_document_enqueues_republish() -> None:
    harness = Harness()
    _, amending, candidate = await _seed(harness)
    response = harness.client.patch(
        f"/api/v1/legal/candidates/{candidate.id}", json={"action": "approve", "note": "ok"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["candidate"]["status"] == "approved"
    assert body["republish_task_id"] == "task-publish"
    assert harness.enqueuer.published == [amending.id]
    assert harness.events == ["commit", "enqueue"]


async def test_review_errors_are_mapped() -> None:
    harness = Harness()
    _, _, candidate = await _seed(harness)
    missing = harness.client.patch(f"/api/v1/legal/candidates/{uuid4()}", json={"action": "reject"})
    assert missing.status_code == 404
    invalid = harness.client.patch(
        f"/api/v1/legal/candidates/{candidate.id}",
        json={"action": "edit", "target_provision_ref": "Điều 1"},
    )
    assert invalid.status_code == 422
    bad_action = harness.client.patch(
        f"/api/v1/legal/candidates/{candidate.id}", json={"action": "delete"}
    )
    assert bad_action.status_code == 422


async def test_publish_enqueues_or_conflicts() -> None:
    harness = Harness()
    _, amending, _ = await _seed(harness)
    accepted = harness.client.post(f"/api/v1/legal/documents/{amending.id}/publish")
    assert accepted.status_code == 202
    assert accepted.json() == {"document_id": str(amending.id), "task_id": "task-publish"}

    uploaded = make_document("7/2026/QH15", status=LegalDocumentStatus.UPLOADED)
    await harness.repository.create_document(uploaded)
    conflict = harness.client.post(f"/api/v1/legal/documents/{uploaded.id}/publish")
    assert conflict.status_code == 409


def test_router_is_not_mounted_when_disabled() -> None:
    from src.server.main import create_app

    app = create_app()
    paths = {getattr(route, "path", "") for route in app.routes}
    assert not any(path.startswith("/api/v1/legal") for path in paths)


@pytest.fixture(autouse=True)
def _no_real_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: object) -> str:
        raise AssertionError("real Celery enqueue in a unit test")

    monkeypatch.setattr(dependencies.LegalTaskEnqueuer, "process", refuse)
    monkeypatch.setattr(dependencies.LegalTaskEnqueuer, "publish", refuse)


async def test_reprocess_failed_document() -> None:
    harness = Harness()
    failed = make_document("8/2026/QH15", status=LegalDocumentStatus.FAILED)
    await harness.repository.create_document(failed)
    response = harness.client.post(f"/api/v1/legal/documents/{failed.id}/reprocess")
    assert response.status_code == 202
    assert response.json() == {"document_id": str(failed.id), "task_id": "task-process"}
    assert harness.enqueuer.processed == [failed.id]
    _, amending, _ = await _seed(harness)
    conflict = harness.client.post(f"/api/v1/legal/documents/{amending.id}/reprocess")
    assert conflict.status_code == 409


async def test_delete_unpublished_document() -> None:
    harness = Harness()
    failed = make_document("8/2026/QH15", status=LegalDocumentStatus.FAILED)
    await harness.repository.create_document(failed)
    response = harness.client.delete(f"/api/v1/legal/documents/{failed.id}")
    assert response.status_code == 204
    assert await harness.repository.get_document(failed.id) is None
    assert harness.events == ["commit"]
    _, amending, _ = await _seed(harness)
    assert harness.client.delete(f"/api/v1/legal/documents/{amending.id}").status_code == 409
    assert harness.client.delete(f"/api/v1/legal/documents/{uuid4()}").status_code == 404
