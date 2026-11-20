"""Request-scoped model-call accounting without prompt logging."""

import pytest

from kira.core.request_trace import request_stage, request_trace
from kira.providers.llm.traced import TracedLLM


@pytest.mark.asyncio
async def test_trace_counts_generate_and_stream_per_stage() -> None:
    class FakeLLM:
        async def generate(self, **kwargs: object) -> str:
            return "answer"

        async def stream(self, **kwargs: object):
            yield "token"

        async def health_check(self) -> bool:
            return True

    llm = TracedLLM(FakeLLM())
    with request_trace() as trace:
        with request_stage("generation"):
            assert await llm.generate(messages=[{"role": "user", "content": "secret"}]) == "answer"
            assert [part async for part in llm.stream(messages=[])] == ["token"]
        assert trace.model_calls == 2
        assert trace.calls_by_stage == {"generation": 2}


@pytest.mark.asyncio
async def test_trace_records_provider_failure() -> None:
    class FailedLLM:
        async def generate(self, **kwargs: object) -> str:
            raise RuntimeError("offline")

        async def stream(self, **kwargs: object):
            yield "unused"

        async def health_check(self) -> bool:
            return False

    with request_trace() as trace:
        with request_stage("quality"):
            with pytest.raises(RuntimeError):
                await TracedLLM(FailedLLM()).generate(messages=[])
        assert trace.model_calls == 1
        assert trace.calls_by_stage == {"quality": 1}
