"""Regression tests for RAG verification and regeneration decisions."""

from typing import Any

import pytest

from src.modules.rag.application.pipeline import RAGPipelineService
from src.modules.rag.orchestration.graph.langgraph_pipeline import LangGraphRAGPipeline
from src.modules.rag.orchestration.state.rag_state import (
    GenerationAgentConfig,
    OrchestratorAgentConfig,
    QualityAgentConfig,
    RAGState,
    RetrievalAgentConfig,
)


class FakeRetrievalAgent:
    """Keep retrieved evidence stable during graph tests."""

    async def handle(self, state: RAGState, context: dict[str, Any]) -> RAGState:
        """Return the input state without external search."""
        return state


class FakeGenerationAgent:
    """Record whether retry feedback reaches generation."""

    def __init__(self) -> None:
        self.feedback: list[str] = []

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
async def test_low_score_falls_back_after_attempt_limit() -> None:
    """The graph must not expose the final low-quality draft as accepted."""
    pipeline, _, quality = make_pipeline([(0.2, True, True)] * 2)

    state = await pipeline.run("Question", "user-1")

    assert quality.calls == 2
    assert state["should_fallback"] is True
    assert state["fallback_reason"] == "quality_gate_failed"
    assert state["final_response"] == ""
