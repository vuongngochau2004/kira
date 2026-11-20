"""Security regressions for bounded uploads and RAG stream disclosure."""

import asyncio
import io
import json
import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.testclient import TestClient
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from kira.auth import dependencies as auth_dependencies
from kira.auth import rate_limit
from kira.auth.dependencies import get_current_user
from kira.chat import repository as conversation_repository
from kira.chat import router as chat_endpoints
from kira.chat.handlers.rag import RAGHandler
from kira.chat.intent.base import ClassificationResult, Intent
from kira.chat.rag.dto import RAGExecutionResult
from kira.db.models import Conversation, Message
from kira.db.session import get_session
from kira.documents import router as document_endpoints
from kira.legal import router as legal_endpoints


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
    async def run_stream(self, **kwargs: object) -> AsyncIterator[dict[str, object]]:
        yield {"mode": "custom", "chunk": {"kind": "attempt_start", "attempt": 1}}
        yield {
            "mode": "custom",
            "chunk": {"kind": "token", "attempt": 1, "text": "Unverified answer"},
        }
        yield {"mode": "updates", "chunk": {"quality": {"should_fallback": True}}}

    async def finalize(self, query: str, state: dict[str, object]) -> RAGExecutionResult:
        return RAGExecutionResult(
            content="Insufficient evidence.",
            citations=[],
            metadata={"rejection_detected": True},
            rejected=True,
        )


async def test_rag_preview_is_marked_and_replaced_by_verified_final_content() -> None:
    handler = RAGHandler(RejectingRagService())
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    events = [event async for event in handler.handle_stream("question", "user-1", classification)]

    assert [event["data"] for event in events if event["type"] == "content"] == [
        {"text": "Unverified answer", "provisional": True, "attempt": 1}
    ]
    assert [event["data"] for event in events if event["type"] == "content_replace"] == [
        {"text": "Insufficient evidence.", "provisional": False}
    ]
    assert events[-2]["data"]["citations"] == []
    assert events[-1]["type"] == "done"


class RetryingRagService(RejectingRagService):
    async def run_stream(self, **kwargs: object) -> AsyncIterator[dict[str, object]]:
        yield {"mode": "custom", "chunk": {"kind": "attempt_start", "attempt": 1}}
        yield {"mode": "custom", "chunk": {"kind": "token", "attempt": 1, "text": "bad"}}
        yield {"mode": "custom", "chunk": {"kind": "attempt_start", "attempt": 2}}
        yield {"mode": "custom", "chunk": {"kind": "token", "attempt": 2, "text": "good"}}
        yield {"mode": "updates", "chunk": {"quality": {"is_final": True}}}

    async def finalize(self, query: str, state: dict[str, object]) -> RAGExecutionResult:
        return RAGExecutionResult(content="good", citations=[], metadata={})


async def test_rag_retry_clears_previous_attempt_before_new_tokens() -> None:
    handler = RAGHandler(RetryingRagService())
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)
    events = [event async for event in handler.handle_stream("question", "user-1", classification)]

    content_events = [event for event in events if event["type"] in {"content", "content_replace"}]
    assert [event["data"] for event in content_events] == [
        {"text": "bad", "provisional": True, "attempt": 1},
        {"text": "", "provisional": True, "attempt": 2},
        {"text": "good", "provisional": True, "attempt": 2},
        {"text": "good", "provisional": False},
    ]


class FailedRagService(RejectingRagService):
    async def run_stream(self, **kwargs: object) -> AsyncIterator[dict[str, object]]:
        yield {"mode": "custom", "chunk": {"kind": "attempt_start", "attempt": 1}}
        yield {"mode": "custom", "chunk": {"kind": "token", "attempt": 1, "text": "draft"}}
        yield {"mode": "error", "chunk": RuntimeError("internal provider detail")}

    async def finalize(self, query: str, state: dict[str, object]) -> RAGExecutionResult:
        raise AssertionError("A failed stream must not finalize a draft")


async def test_rag_stream_error_clears_preview_without_finalizing_draft() -> None:
    handler = RAGHandler(FailedRagService())
    classification = ClassificationResult(intent=Intent.RAG, confidence=0.9)

    events = [event async for event in handler.handle_stream("question", "user-1", classification)]

    assert [event["type"] for event in events if event["type"] in {"error", "done"}] == [
        "error",
        "done",
    ]
    assert [event["data"] for event in events if event["type"] == "content_replace"] == [
        {"text": "", "provisional": True}
    ]
    assert not any(event["type"] == "metadata" for event in events)
    assert "internal provider detail" not in str(events)


class FakeStreamUseCase:
    def __init__(self, *, wait_for_cancel: bool = False) -> None:
        self.wait_for_cancel = wait_for_cancel
        self.closed = False

    async def execute_stream(self, query: object) -> AsyncIterator[dict[str, object]]:
        try:
            yield {
                "type": "content",
                "data": {"text": "unverified", "provisional": True, "attempt": 1},
            }
            if self.wait_for_cancel:
                await asyncio.Event().wait()
            yield {"type": "content_replace", "data": {"text": "verified", "provisional": False}}
            yield {"type": "metadata", "data": {"citations": []}}
            yield {"type": "done"}
        finally:
            self.closed = True


async def test_stream_message_pair_commits_once_after_both_inserts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation_id = uuid.uuid4()
    message_id = uuid.uuid4()

    class FakeSession:
        commits = 0

        async def commit(self) -> None:
            self.commits += 1

    session = FakeSession()
    created_roles: list[str] = []

    async def ensure_conversation(*args: object, **kwargs: object) -> uuid.UUID:
        assert kwargs["commit"] is False
        assert session.commits == 0
        return conversation_id

    async def create_message(*args: object, **kwargs: object) -> SimpleNamespace:
        assert kwargs["commit"] is False
        assert session.commits == 0
        created_roles.append(str(kwargs["role"]))
        return SimpleNamespace(id=message_id)

    monkeypatch.setattr(chat_endpoints, "_ensure_conversation_exists", ensure_conversation)
    monkeypatch.setattr(chat_endpoints, "create_message", create_message)

    saved = await chat_endpoints._save_streamed_messages(
        None, uuid.uuid4(), "question", ["verified"], [], {}, session
    )

    assert saved == (conversation_id, message_id)
    assert created_roles == ["user", "assistant"]
    assert session.commits == 1


async def test_chat_repository_flushes_ids_without_early_commit() -> None:
    """The real repository must leave the new conversation and both messages uncommitted."""

    class TrackingSession:
        def __init__(self) -> None:
            self.added: list[Conversation | Message] = []
            self.commits = 0
            self.flushes = 0
            self.executions = 0

        def add(self, item: Conversation | Message) -> None:
            self.added.append(item)

        async def execute(self, statement: object) -> None:
            self.executions += 1

        async def flush(self) -> None:
            self.flushes += 1
            for item in self.added:
                if item.id is None:
                    item.id = uuid.uuid4()

        async def refresh(self, item: Conversation | Message) -> None:
            assert isinstance(item.id, uuid.UUID)

        async def commit(self) -> None:
            self.commits += 1

    session = TrackingSession()
    db = cast(AsyncSession, session)
    conversation = await conversation_repository.create_conversation(
        user_id=uuid.uuid4(), title="question", db=db, commit=False
    )
    user_message = await conversation_repository.create_message(
        conversation_id=conversation.id, role="user", content="question", db=db, commit=False
    )
    assistant_message = await conversation_repository.create_message(
        conversation_id=conversation.id, role="assistant", content="answer", db=db, commit=False
    )

    assert all(isinstance(item.id, uuid.UUID) for item in session.added)
    assert [item.id for item in session.added] == [
        conversation.id,
        user_message.id,
        assistant_message.id,
    ]
    assert session.flushes == 3
    assert session.executions == 2
    assert session.commits == 0


async def test_stream_saves_only_authoritative_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_case = FakeStreamUseCase()

    async def get_use_case() -> FakeStreamUseCase:
        return use_case

    saved_content: list[str] = []

    async def save_messages(
        conversation_id: uuid.UUID | None,
        user_id: uuid.UUID,
        query: str,
        full_content: list[str],
        citations: list[object],
        metadata: dict[str, object],
        db: object,
    ) -> tuple[uuid.UUID, uuid.UUID]:
        saved_content.extend(full_content)
        return uuid.uuid4(), uuid.uuid4()

    monkeypatch.setattr(chat_endpoints, "get_chat_use_case", get_use_case)
    monkeypatch.setattr(chat_endpoints, "_save_streamed_messages", save_messages)
    stream = chat_endpoints._stream_generator("question", uuid.uuid4(), None, None)
    events = [json.loads(item.removeprefix("data: ")) for item in [event async for event in stream]]

    assert saved_content == ["verified"]
    assert [event["type"] for event in events].count("metadata") == 1
    assert [event["type"] for event in events].count("done") == 1
    assert use_case.closed


async def test_handler_error_events_are_not_duplicated_by_sse_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A handler reset/error/done sequence must not trigger another reset or save."""

    class FailingUseCase:
        async def execute_stream(self, query: object) -> AsyncIterator[dict[str, object]]:
            yield {
                "type": "content",
                "data": {"text": "draft", "provisional": True, "attempt": 1},
            }
            yield {"type": "content_replace", "data": {"text": "", "provisional": True}}
            yield {"type": "error", "data": {"error": "internal provider detail"}}
            yield {"type": "done"}

    async def get_use_case() -> FailingUseCase:
        return FailingUseCase()

    async def fail_save(*args: object, **kwargs: object) -> None:
        raise AssertionError("A failed preview must not be saved")

    monkeypatch.setattr(chat_endpoints, "get_chat_use_case", get_use_case)
    monkeypatch.setattr(chat_endpoints, "_save_streamed_messages", fail_save)
    stream = chat_endpoints._stream_generator("question", uuid.uuid4(), None, None)
    events = [json.loads(item.removeprefix("data: ")) async for item in stream]
    types = [event["type"] for event in events]

    assert types == ["content", "content_replace", "error", "done"]
    assert events[1]["data"] == {"text": "", "provisional": True}
    assert events[2]["data"] == {"error": "Chat stream failed"}
    assert "internal provider detail" not in str(events)


async def test_closing_sse_stream_closes_upstream_without_saving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_case = FakeStreamUseCase(wait_for_cancel=True)

    async def get_use_case() -> FakeStreamUseCase:
        return use_case

    async def fail_save(*args: object, **kwargs: object) -> None:
        raise AssertionError("A cancelled preview must not be saved")

    monkeypatch.setattr(chat_endpoints, "get_chat_use_case", get_use_case)
    monkeypatch.setattr(chat_endpoints, "_save_streamed_messages", fail_save)
    stream = chat_endpoints._stream_generator("question", uuid.uuid4(), None, None)
    first_event = json.loads((await anext(stream)).removeprefix("data: "))
    assert first_event["type"] == "content"
    await stream.aclose()
    assert use_case.closed


async def test_stream_error_and_done_emit_one_terminal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A handler error after a preview must not duplicate terminal SSE events."""

    class FailedStreamUseCase:
        async def execute_stream(self, query: object) -> AsyncIterator[dict[str, object]]:
            yield {
                "type": "content",
                "data": {"text": "draft", "provisional": True, "attempt": 1},
            }
            yield {"type": "content_replace", "data": {"text": "", "provisional": True}}
            yield {"type": "error", "data": {"error": "private provider detail"}}
            yield {"type": "done"}

    async def get_use_case() -> FailedStreamUseCase:
        return FailedStreamUseCase()

    async def fail_save(*args: object, **kwargs: object) -> None:
        raise AssertionError("Failed stream must not persist a draft")

    monkeypatch.setattr(chat_endpoints, "get_chat_use_case", get_use_case)
    monkeypatch.setattr(chat_endpoints, "_save_streamed_messages", fail_save)

    stream = chat_endpoints._stream_generator("question", uuid.uuid4(), None, None)
    events = [json.loads(event.removeprefix("data: ")) async for event in stream]

    assert [item["type"] for item in events].count("content_replace") == 1
    assert [item["type"] for item in events].count("error") == 1
    assert [item["type"] for item in events].count("done") == 1
    assert "private provider detail" not in str(events)


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
