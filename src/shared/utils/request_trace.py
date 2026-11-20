"""Request-local timing and model-call counters for chat workflows."""

import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Iterator
from uuid import uuid4

from loguru import logger


@dataclass
class RequestTrace:
    """Bounded counters that never contain user or document content."""

    request_id: str = field(default_factory=lambda: str(uuid4()))
    model_calls: int = 0
    calls_by_stage: dict[str, int] = field(default_factory=dict)


_trace: ContextVar[RequestTrace | None] = ContextVar("chat_request_trace", default=None)
_stage: ContextVar[str] = ContextVar("chat_request_stage", default="unknown")


@contextmanager
def request_trace() -> Iterator[RequestTrace]:
    """Create one trace for a non-stream or stream chat request."""
    trace = RequestTrace()
    token = _trace.set(trace)
    try:
        yield trace
    finally:
        logger.info(
            "chat_trace request_id={} model_calls={} calls_by_stage={}",
            trace.request_id,
            trace.model_calls,
            trace.calls_by_stage,
        )
        _trace.reset(token)


@contextmanager
def request_stage(name: str) -> Iterator[None]:
    """Record stage wall time while preserving the current async request trace."""
    started = time.perf_counter()
    token = _stage.set(name)
    try:
        yield
    finally:
        trace = _trace.get()
        if trace is not None:
            logger.info(
                "chat_stage request_id={} stage={} duration_ms={}",
                trace.request_id,
                name,
                round((time.perf_counter() - started) * 1000),
            )
        _stage.reset(token)


def record_model_call(duration_ms: float, outcome: str) -> None:
    """Count one provider invocation in the active stage."""
    trace = _trace.get()
    if trace is None:
        return
    stage = _stage.get()
    trace.model_calls += 1
    trace.calls_by_stage[stage] = trace.calls_by_stage.get(stage, 0) + 1
    logger.info(
        "chat_model_call request_id={} stage={} duration_ms={} outcome={}",
        trace.request_id,
        stage,
        round(duration_ms),
        outcome,
    )
