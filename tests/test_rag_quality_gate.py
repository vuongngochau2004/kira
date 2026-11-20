"""Regression tests for RAG verification and regeneration decisions."""

import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest

from src.modules.rag.application.pipeline import RAGPipelineService
from src.modules.rag.orchestration.agents.generation_agent import GenerationAgent
from src.modules.rag.orchestration.graph.langgraph_pipeline import LangGraphRAGPipeline
from src.modules.rag.orchestration.state.rag_state import (
    GenerationAgentConfig,
    OrchestratorAgentConfig,
    QualityAgentConfig,
    RAGState,
    RetrievalAgentConfig,
    create_initial_state,
)
from src.shared.ports.llm import LLMPort


class FakeRetrievalAgent:
    """Keep retrieved evidence stable during graph tests."""

    async def handle(self, state: RAGState, context: dict[str, Any]) -> RAGState:
        """Return the input state without external search."""
        return state


class FakeGenerationAgent:
    """Record whether retry feedback reaches generation."""

    def __init__(self) -> None:
        self.feedback: list[str] = []
        self.stream_calls = 0

    async def handle(self, state: RAGState, context: dict[str, Any]) -> RAGState:
        """Generate an initial draft."""
        state["generated_response"] = "Initial draft"
        state["final_response"] = "Initial draft"
        return state

    async def regenerate_with_feedback(self, state: RAGState, feedback: str) -> RAGState:
        """Record feedback and generate a new draft."""
        self.feedback.append(feedback)
        state["generated_response"] = "Revised draft"
        state["final_response"] = "Revised draft"
        return state

    async def generate_for_graph_stream(
        self,
        state: RAGState,
        on_token: Callable[[str], None],
        feedback: str | None = None,
    ) -> RAGState:
        """Emit a token before the graph's quality node can finish."""
        self.stream_calls += 1
        if feedback is None:
            state["generated_response"] = "Initial draft"
            state["final_response"] = "Initial draft"
            on_token("Initial draft")
        else:
            self.feedback.append(feedback)
            state["generated_response"] = "Revised draft"
            state["final_response"] = "Revised draft"
            on_token("Revised draft")
        return state


class FakeQualityAgent:
    """Return successive quality decisions to the graph."""

    def __init__(self, decisions: list[tuple[float, bool, bool]]) -> None:
        self.decisions = decisions
        self.calls = 0

    async def handle(self, state: RAGState, context: dict[str, Any]) -> RAGState:
        """Set quality output for this attempt."""
        score, verified, regenerate = self.decisions[self.calls]
        self.calls += 1
        state["quality_agent_output"] = {
            "quality_score": score,
            "verification": {"is_verified": verified},
            "critique": {"issues": ["Unsupported claim"]},
            "suggestions": ["Cite the source"],
            "should_regenerate": regenerate,
        }
        return state


def make_pipeline(
    decisions: list[tuple[float, bool, bool]], max_attempts: int = 2
) -> tuple[LangGraphRAGPipeline, FakeGenerationAgent, FakeQualityAgent]:
    """Create a graph with deterministic agents and bounded attempts."""
    pipeline = LangGraphRAGPipeline(
        orchestrator_config=OrchestratorAgentConfig(max_pipeline_iterations=max_attempts),
        retrieval_config=RetrievalAgentConfig(),
        generation_config=GenerationAgentConfig(),
        quality_config=QualityAgentConfig(),
    )
    generation = FakeGenerationAgent()
    quality = FakeQualityAgent(decisions)
    pipeline.retrieval_agent = FakeRetrievalAgent()  # type: ignore[assignment]
    pipeline.generation_agent = generation  # type: ignore[assignment]
    pipeline.quality_agent = quality  # type: ignore[assignment]
    return pipeline, generation, quality


@pytest.mark.asyncio
async def test_unverified_answer_falls_back_even_with_high_score() -> None:
    """A numeric score must never override failed verification."""
    pipeline, generation, quality = make_pipeline([(0.95, False, True)] * 2)

    state = await pipeline.run("Question", "user-1")
    result = await RAGPipelineService(pipeline).finalize("Question", state)

    assert quality.calls == 2
    assert generation.feedback == ["Unsupported claim\nCite the source"]
    assert state["should_fallback"] is True
    assert state["fallback_reason"] == "verification_failed"
    assert result.rejected is True
    assert result.citations == []
    assert "Initial draft" not in result.content
    assert "Revised draft" not in result.content


@pytest.mark.asyncio
async def test_regeneration_uses_feedback_then_accepts_verified_answer() -> None:
    """A verified revision can complete after a failed first draft."""
    pipeline, generation, quality = make_pipeline([(0.4, False, True), (0.9, True, False)])

    state = await pipeline.run("Question", "user-1")

    assert quality.calls == 2
    assert generation.feedback == ["Unsupported claim\nCite the source"]
    assert state["should_fallback"] is False
    assert state["is_final"] is True
    assert state["final_response"] == "Revised draft"


@pytest.mark.asyncio
async def test_stream_and_non_stream_finalize_with_same_answer_and_citations() -> None:
    """Both compiled graph entrypoints pass identical evidence to the finalizer."""

    class CitedGeneration(FakeGenerationAgent):
        @staticmethod
        def _cite(state: RAGState) -> RAGState:
            state["final_citations"] = [
                {"filename": "contract.pdf", "text": "Effective January 1", "page_number": 1}
            ]
            return state

        async def handle(self, state: RAGState, context: dict[str, Any]) -> RAGState:
            return self._cite(await super().handle(state, context))

        async def generate_for_graph_stream(
            self,
            state: RAGState,
            on_token: Callable[[str], None],
            feedback: str | None = None,
        ) -> RAGState:
            return self._cite(await super().generate_for_graph_stream(state, on_token, feedback))

    class RelevanceLLM:
        async def generate(self, **kwargs: Any) -> str:
            return '{"has_relevant_docs": true}'

    async def finished(streaming: bool) -> tuple[str, list[str]]:
        pipeline, _, _ = make_pipeline([(0.9, True, False)])
        pipeline.generation_agent = CitedGeneration()  # type: ignore[assignment]
        pipeline.llm = RelevanceLLM()  # type: ignore[assignment]
        if streaming:
            state = None
            async for event in pipeline.run_stream("Question", "user-1"):
                if event["mode"] == "updates":
                    state = next(iter(event["chunk"].values()))
            assert state is not None
        else:
            state = await pipeline.run("Question", "user-1")
        result = await RAGPipelineService(pipeline).finalize("Question", state)
        return result.content, [citation.filename for citation in result.citations]

    assert await finished(False) == await finished(True)


@pytest.mark.asyncio
async def test_low_score_falls_back_after_attempt_limit() -> None:
    """The graph must not expose the final low-quality draft as accepted."""
    pipeline, _, quality = make_pipeline([(0.2, True, True)] * 2)

    state = await pipeline.run("Question", "user-1")

    assert quality.calls == 2
    assert state["should_fallback"] is True
    assert state["fallback_reason"] == "quality_gate_failed"
    assert state["final_response"] == ""


@pytest.mark.asyncio
async def test_graph_stream_emits_provider_token_before_quality_completes() -> None:
    """The compiled graph exposes its generation token through the custom channel."""
    pipeline, generation, quality = make_pipeline([(0.9, True, False)])
    stream = pipeline.run_stream("Question", "user-1")
    try:
        token = None
        for _ in range(6):
            event = await asyncio.wait_for(anext(stream), timeout=2)
            if event["mode"] == "custom" and event["chunk"].get("kind") == "token":
                token = event["chunk"]
                break
        assert token == {"kind": "token", "attempt": 1, "text": "Initial draft"}
        assert generation.stream_calls == 1
        assert quality.calls == 0
    finally:
        await asyncio.wait_for(stream.aclose(), timeout=2)


class BlockingLLM(LLMPort):
    """Hold a provider stream open after its first token to test cancellation."""

    def __init__(self) -> None:
        self.closed = False
        self.generate_calls = 0

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        self.generate_calls += 1
        return "unexpected"

    async def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        try:
            yield "first"
            await asyncio.Event().wait()
        finally:
            self.closed = True

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_cancelled_generation_closes_provider_stream() -> None:
    """A cancelled graph generation does not leave the provider iterator running."""
    llm = BlockingLLM()
    agent = GenerationAgent(GenerationAgentConfig(), llm_client=llm)
    first_token = asyncio.Event()
    tokens: list[str] = []

    def collect_token(token: str) -> None:
        tokens.append(token)
        first_token.set()

    task = asyncio.create_task(
        agent.generate_for_graph_stream(create_initial_state("Question", "user-1"), collect_token)
    )
    await asyncio.wait_for(first_token.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert tokens == ["first"]
    assert llm.closed
    assert llm.generate_calls == 0
