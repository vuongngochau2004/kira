from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.modules.legal.application.errors import LegalTextExtractionError
from src.modules.legal.application.records import LegalDocumentStatus
from src.modules.legal.infrastructure.text_extractor import DocumentModuleTextExtractor
from src.worker import legal_tasks
from src.worker.celery_app import celery_app
from src.worker.event_loop import get_worker_event_loop


def test_legal_tasks_are_registered() -> None:
    assert "legal.process" in celery_app.tasks
    assert "legal.publish" in celery_app.tasks
    assert "src.worker.legal_tasks" in celery_app.conf.include


def test_worker_event_loop_is_shared_and_recreated_after_close() -> None:
    loop = get_worker_event_loop()
    assert get_worker_event_loop() is loop
    loop.close()
    assert get_worker_event_loop() is not loop


async def test_text_extractor_reads_plain_text() -> None:
    text = await DocumentModuleTextExtractor().extract_text(
        "Điều 1. Phạm vi\nNội dung “trích”.".encode(), "txt"
    )
    assert text.startswith("Điều 1. Phạm vi")


async def test_text_extractor_rejects_empty_content() -> None:
    with pytest.raises(LegalTextExtractionError):
        await DocumentModuleTextExtractor().extract_text(b"   ", "txt")


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class _FakeService:
    def __init__(self, status: LegalDocumentStatus) -> None:
        self.status = status
        self.received = None

    async def execute(self, document_id):
        self.received = document_id
        return SimpleNamespace(status=self.status, error_detail=None)


class _FakeGraph:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


async def test_run_process_commits_and_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    service = _FakeService(LegalDocumentStatus.IN_REVIEW)
    monkeypatch.setattr(legal_tasks, "async_session_factory", lambda: session)
    monkeypatch.setattr(legal_tasks, "process_legal_document_service", lambda db: service)
    document_id = uuid4()

    result = await legal_tasks.run_process(str(document_id))

    assert result == {"document_id": str(document_id), "status": "in_review", "error": None}
    assert service.received == document_id
    assert session.commits == 1


class _FakePublishService(_FakeService):
    def __init__(self, republish_ids: list) -> None:
        super().__init__(LegalDocumentStatus.PUBLISHED)
        self.republish_ids = republish_ids

    async def execute(self, document_id):
        document = await super().execute(document_id)
        return SimpleNamespace(document=document, republish_document_ids=self.republish_ids)


async def test_run_publish_closes_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    graph = _FakeGraph()
    dependent = uuid4()
    service = _FakePublishService([dependent])
    monkeypatch.setattr(legal_tasks, "async_session_factory", lambda: session)
    monkeypatch.setattr(legal_tasks, "legal_graph", lambda: graph)
    monkeypatch.setattr(legal_tasks, "publish_legal_document_service", lambda db, g: service)

    result = await legal_tasks.run_publish(str(uuid4()))

    assert result["status"] == "published"
    assert result["republish_ids"] == [str(dependent)]
    assert graph.closed
    assert session.commits == 1


def test_publish_task_enqueues_dependent_republishes(monkeypatch: pytest.MonkeyPatch) -> None:
    dependent = str(uuid4())
    queued: list[str] = []

    async def fake_run_publish(document_id: str) -> dict:
        return {
            "document_id": document_id,
            "status": "published",
            "error": None,
            "republish_ids": [dependent],
        }

    monkeypatch.setattr(legal_tasks, "run_publish", fake_run_publish)
    monkeypatch.setattr(legal_tasks.publish_legal_document_task, "delay", queued.append)

    result = legal_tasks.publish_legal_document_task(str(uuid4()))

    assert result["republish_ids"] == [dependent]
    assert queued == [dependent]
