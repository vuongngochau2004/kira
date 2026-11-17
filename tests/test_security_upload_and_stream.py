"""Security regressions for bounded uploads and RAG stream disclosure."""

import io
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from src.modules.chat.infrastructure.handlers.rag_handler import RAGHandler
from src.modules.document.api import endpoints as document_endpoints
from src.modules.legal.api import endpoints as legal_endpoints
from src.modules.rag.application.dto import RAGExecutionResult
from src.shared.infrastructure.auth import dependencies as auth_dependencies
from src.shared.infrastructure.auth import rate_limit
from src.shared.infrastructure.auth.dependencies import get_current_user
from src.shared.infrastructure.persistence.database.session import get_session
from src.shared.ports.classification import ClassificationResult, Intent


@pytest.mark.parametrize(
    ("module", "reader", "limit_name"),
    [
        (document_endpoints, document_endpoints._read_bounded_upload, "MAX_UPLOAD_FILE_BYTES"),
        (legal_endpoints, legal_endpoints._read_bounded_legal_upload, "MAX_LEGAL_UPLOAD_BYTES"),
    ],
)
async def test_upload_reader_rejects_oversized_file(
    monkeypatch: pytest.MonkeyPatch, module: object, reader: object, limit_name: str
) -> None:
    monkeypatch.setattr(module, limit_name, 3)
    file = UploadFile(file=io.BytesIO(b"1234"), filename="large.txt")

    with pytest.raises(HTTPException) as error:
        await reader(file)

    assert error.value.status_code == 413


def test_document_download_rejects_query_token_without_cookie_or_header() -> None:
    app = FastAPI()
    app.include_router(document_endpoints.router, prefix="/documents")
    app.dependency_overrides[get_session] = lambda: None

    response = TestClient(app).get(
        "/documents/00000000-0000-0000-0000-000000000001/download?token=secret"
    )

    assert response.status_code == 401


def test_document_download_rejects_refresh_token_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    app.include_router(document_endpoints.router, prefix="/documents")
    app.dependency_overrides[get_session] = lambda: None
    monkeypatch.setattr(
        auth_dependencies,
        "decode_token",
        lambda token: {"sub": "user-1", "type": "refresh"},
    )

    client = TestClient(app)
    client.cookies.set("access_token", "refresh-token")
    response = client.get("/documents/00000000-0000-0000-0000-000000000001/download")

    assert response.status_code == 401


def test_document_upload_rejects_more_than_ten_files() -> None:
    app = FastAPI()
    app.include_router(document_endpoints.router, prefix="/documents")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    app.dependency_overrides[get_session] = lambda: None
    app.dependency_overrides[document_endpoints.limit_document_upload] = lambda: None
    files = [("files", (f"file-{index}.txt", b"x", "text/plain")) for index in range(11)]

    response = TestClient(app).post("/documents/upload", files=files)

    assert response.status_code == 413


class RejectingRagService:
    async def run_stream(self, **kwargs: object):
        yield {"mode": "messages", "chunk": SimpleNamespace(content="Unverified answer")}
        yield {"mode": "updates", "chunk": {"quality": {"should_fallback": True}}}

    async def finalize(self, query: str, state: dict[str, object]) -> RAGExecutionResult:
        return RAGExecutionResult(
            content="Insufficient evidence.",
            citations=[],
            metadata={"rejection_detected": True},
            rejected=True,
        )


async def test_rag_stream_only_emits_verified_final_content() -> None:
    handler = RAGHandler(RejectingRagService())
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    events = [event async for event in handler.handle_stream("question", "user-1", classification)]

    assert [event["data"]["text"] for event in events if event["type"] == "content"] == [
        "Insufficient evidence."
    ]
    assert events[-2]["data"]["citations"] == []
    assert events[-1]["type"] == "done"


class FailedRagService(RejectingRagService):
    async def run_stream(self, **kwargs: object) -> AsyncIterator[dict[str, object]]:
        yield {"mode": "updates", "chunk": {"generation": {"generated_response": "draft"}}}
        yield {"mode": "error", "chunk": RuntimeError("internal provider detail")}

    async def finalize(self, query: str, state: dict[str, object]) -> RAGExecutionResult:
        raise AssertionError("A failed stream must not finalize a draft")


async def test_rag_stream_error_does_not_finalize_or_expose_draft() -> None:
    handler = RAGHandler(FailedRagService())
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    events = [event async for event in handler.handle_stream("question", "user-1", classification)]

    assert [event["type"] for event in events if event["type"] in {"error", "done"}] == [
        "error",
        "done",
    ]
    assert not any(event["type"] == "content" for event in events)
    assert "internal provider detail" not in str(events)


class FakeRedis:
    calls: dict[str, int] = {}

    @classmethod
    def from_url(cls, url: str, **kwargs: object) -> "FakeRedis":
        assert url.startswith("redis://") or url.startswith("rediss://")
        return cls(**kwargs)

    def __init__(self, **kwargs: object) -> None:
        self.closed = False

    async def eval(self, script: str, key_count: int, key: str, expiry: int) -> int:
        assert key_count == 1 and expiry > 0 and "INCR" in script
        self.calls[key] = self.calls.get(key, 0) + 1
        return self.calls[key]

    async def aclose(self) -> None:
        self.closed = True


async def test_redis_rate_limit_rejects_request_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeRedis.calls = {}
    monkeypatch.setattr(rate_limit, "Redis", FakeRedis)

    await rate_limit._check_limit("chat", "user:123", maximum=2, window_seconds=60)
    await rate_limit._check_limit("chat", "user:123", maximum=2, window_seconds=60)
    with pytest.raises(HTTPException) as error:
        await rate_limit._check_limit("chat", "user:123", maximum=2, window_seconds=60)

    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "60"}
    assert all("user:123" not in key for key in FakeRedis.calls)


class UnavailableRedis(FakeRedis):
    async def eval(self, script: str, key_count: int, key: str, expiry: int) -> int:
        raise RedisError("connection unavailable")


async def test_redis_rate_limit_fails_closed_when_storage_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rate_limit, "Redis", UnavailableRedis)

    with pytest.raises(HTTPException) as error:
        await rate_limit._check_limit("login", "ip:127.0.0.1", maximum=10, window_seconds=60)

    assert error.value.status_code == 503
    assert error.value.detail == "Request limit service unavailable"
