"""Pipeline-trace status events emitted by the RAG chat handler."""

from kira.chat.handlers.rag import RAGHandler


def _quality_state(**overrides: object) -> dict:
    state: dict = {
        "orchestrator_state": {"iteration_count": 1},
        "routing_decision": "regenerate",
        "should_fallback": False,
        "quality_agent_output": {
            "quality_score": 0.62,
            "should_regenerate": True,
            "critique": {"issues": ["Response too short"]},
            "verification": {"is_verified": False},
        },
    }
    state.update(overrides)
    return state


def test_quality_step_reports_regenerate_decision_and_timing() -> None:
    event = RAGHandler._status_event("quality", _quality_state(), duration_ms=6405)

    assert event["type"] == "status"
    assert event["data"]["stage"] == "quality"
    metadata = event["data"]["metadata"]
    assert metadata["duration_ms"] == 6405
    assert metadata["iteration"] == 1
    assert metadata["decision"] == "regenerate"
    assert metadata["quality_score"] == 0.62
    assert metadata["verified"] is False
    assert "issues" not in metadata


def test_quality_step_reports_pass_and_fallback() -> None:
    passed = RAGHandler._status_event("quality", _quality_state(routing_decision="end"), 10)
    fallback = RAGHandler._status_event(
        "quality", _quality_state(routing_decision="end", should_fallback=True), 10
    )

    assert passed["data"]["metadata"]["decision"] == "pass"
    assert fallback["data"]["metadata"]["decision"] == "fallback"


def test_retrieval_step_counts_reranked_documents() -> None:
    state = {
        "retrieval_agent_output": {
            "retrieved_docs": [{}, {}, {}],
            "reranked_docs": [{}, {}],
            "refined_queries": ["q1"],
        }
    }

    metadata = RAGHandler._status_event("retrieval", state, 600)["data"]["metadata"]

    assert metadata["docs_retrieved"] == 2
    assert metadata["refined_queries"] == ["q1"]
    assert metadata["iteration"] == 0
