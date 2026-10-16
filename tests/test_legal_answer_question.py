from datetime import date

from src.modules.legal.application.answer_question import (
    AnswerLegalQuestion,
    LegalQAOptions,
    LegalQAResult,
    LegalQAStatus,
    LegalQAToken,
)
from src.modules.legal.application.temporal import ResolveTemporalQuery
from src.modules.legal.domain.prompts.legal_qa import GRAPH_UNAVAILABLE_NOTICE
from src.modules.legal.infrastructure.reranker import ConfiguredLegalReranker
from src.shared.ports.legal_graph import ProvisionContext
from tests.legal_fakes import (
    FakeKeywordSearch,
    FakeLegalGraph,
    FakeLLM,
    FakeProvisionSearch,
    make_hit,
)
from tests.test_legal_search_index import FakeEmbedding

TODAY = date(2026, 10, 15)
LAW = "31/2024/QH15"
JULY = date(2026, 7, 1)
OLD = make_hit(f"{LAW}#D3.K1", "1. Quyết định quy hoạch sử dụng đất.", date(2024, 8, 1), JULY)
NEW = make_hit(f"{LAW}#D3.K1", "1. Quyết định quy hoạch và kế hoạch sử dụng đất.", JULY)
DEFINITIONS = make_hit(f"{LAW}#D4", "Điều 4. Giải thích từ ngữ.", date(2024, 8, 1))
GUIDE = make_hit(
    "10/2026/NĐ-CP#D5",
    "Điều 5. Trình tự lập quy hoạch.",
    JULY,
    title="Nghị định hướng dẫn Luật Đất đai",
    doc_type="decree",
)


def _service(*, hits=(OLD, NEW, DEFINITIONS, GUIDE), keywords=None, seed_top_k=20, min_score=0.0):
    llm = FakeLLM()
    graph = FakeLegalGraph()
    search = FakeProvisionSearch(hits)
    service = AnswerLegalQuestion(
        temporal=ResolveTemporalQuery(llm, lambda: TODAY),
        embedding=FakeEmbedding(),
        search=search,
        keywords=keywords or FakeKeywordSearch(),
        graph=graph,
        reranker=ConfiguredLegalReranker(
            enabled=False, mode="llm", llm_client_provider=lambda: None
        ),
        llm=llm,
        options=LegalQAOptions(
            seed_top_k=seed_top_k,
            final_top_k=8,
            max_guides=5,
            snippet_length=200,
            min_score=min_score,
        ),
    )
    return service, llm, graph, search


async def _collect(service, question):
    return [event async for event in service.stream(question)]


async def test_single_date_answer_streams_with_citations_and_guides() -> None:
    service, llm, graph, _ = _service(seed_top_k=2)
    graph.contexts[f"{LAW}#D3.K1"] = ProvisionContext(
        f"{LAW}#D3.K1",
        "Điều 3",
        "Điều 3. Quyền của Nhà nước",
        "99/2026/QH15#D1.K1",
        "99/2026/QH15",
        "Luật sửa đổi Luật Đất đai",
        None,
    )
    graph.guides = ["10/2026/NĐ-CP"]

    events = await _collect(service, "Nhà nước có quyền gì về quy hoạch đất hiện nay?")

    assert isinstance(events[0], LegalQAStatus) and events[0].stage == "temporal"
    assert events[0].metadata == {"mode": "single", "dates": ["2026-10-15"], "source": "rule"}
    assert isinstance(events[1], LegalQAStatus) and events[1].stage == "retrieval"
    assert [e.text for e in events if isinstance(e, LegalQAToken)] == llm.stream_chunks
    result = events[-1]
    assert isinstance(result, LegalQAResult)
    roles = [(c["legal"]["provision_key"], c["legal"]["role"]) for c in result.citations]
    assert roles == [
        (f"{LAW}#D3.K1", "primary"),
        (f"{LAW}#D4", "primary"),
        ("10/2026/NĐ-CP#D5", "guide"),
    ]
    assert result.citations[0]["legal"]["valid_from"] == "2026-07-01"
    user = llm.stream_calls[0][1]["content"]
    assert "Áp dụng tại ngày 15/10/2026." in user
    assert "[1] Khoản 1 — Luật Đất đai số 31/2024/QH15 — hiệu lực 01/07/2026 → nay" in user
    assert "được sửa đổi bởi Luật sửa đổi Luật Đất đai số 99/2026/QH15" in user
    assert result.notices == []


async def test_past_date_uses_old_version_and_flags_later_amendment() -> None:
    service, llm, graph, _ = _service()
    graph.contexts[f"{LAW}#D3.K1"] = ProvisionContext(
        f"{LAW}#D3.K1", None, None, None, None, None, JULY
    )

    events = await _collect(service, "Năm 2025 quy định về quy hoạch đất thế nào?")

    result = events[-1]
    texts = [c["text"] for c in result.citations]
    assert OLD.text in texts and NEW.text not in texts and GUIDE.text not in texts
    first = result.citations[0]["legal"]
    assert (first["provision_key"], first["amended_after"]) == (f"{LAW}#D3.K1", "2026-07-01")
    assert "đã được sửa đổi từ ngày 01/07/2026" in llm.stream_calls[0][1]["content"]


async def test_graph_failure_still_answers_with_notice() -> None:
    service, llm, graph, _ = _service()
    graph.fail_reads = True
    events = await _collect(service, "Quy hoạch đất hiện nay quy định thế nào?")
    result = events[-1]
    assert result.notices == [GRAPH_UNAVAILABLE_NOTICE]
    assert result.citations
    assert GRAPH_UNAVAILABLE_NOTICE in llm.stream_calls[0][1]["content"]


async def test_keyword_failure_falls_back_to_dense() -> None:
    service, _, _, _ = _service(keywords=FakeKeywordSearch(fail=True))
    events = await _collect(service, "Quy hoạch đất hiện nay?")
    assert events[-1].citations


async def test_no_provision_in_force_answers_not_found_without_llm() -> None:
    service, llm, _, _ = _service(hits=(GUIDE,))
    events = await _collect(service, "Năm 2025 quy định thế nào?")
    tokens = [e.text for e in events if isinstance(e, LegalQAToken)]
    assert len(tokens) == 1 and tokens[0].startswith("Áp dụng tại ngày 31/12/2025. Không tìm thấy")
    assert llm.stream_calls == []
    assert events[-1].citations == []


async def test_compare_mode_pairs_changed_versions() -> None:
    service, llm, graph, _ = _service(hits=(OLD, NEW, DEFINITIONS))
    graph.contexts[f"{LAW}#D3.K1"] = ProvisionContext(
        f"{LAW}#D3.K1", None, None, "99/2026/QH15#D1.K1", "99/2026/QH15", "Luật sửa đổi", None
    )

    events = await _collect(service, "So sánh quy định về quy hoạch trước và sau 1/7/2026")

    result = events[-1]
    assert result.temporal.mode == "compare"
    roles = [(c["legal"]["provision_key"], c["legal"]["role"]) for c in result.citations]
    assert (f"{LAW}#D3.K1", "before") in roles and (f"{LAW}#D3.K1", "after") in roles
    assert (f"{LAW}#D4", "primary") in roles
    user = llm.stream_calls[0][1]["content"]
    assert "So sánh quy định tại ngày 30/06/2026 và ngày 01/07/2026." in user
    assert "(Quy định trước thay đổi)" in user
    assert "được sửa đổi bởi Luật sửa đổi số 99/2026/QH15" in user


async def test_result_is_always_last_and_unique() -> None:
    service, _, _, _ = _service()
    events = await _collect(service, "Quy hoạch đất hiện nay?")
    results = [e for e in events if isinstance(e, LegalQAResult)]
    assert len(results) == 1 and events[-1] is results[0]


async def test_irrelevant_seeds_below_floor_answer_not_found() -> None:
    service, llm, _, search = _service(min_score=0.8, keywords=FakeKeywordSearch([DEFINITIONS]))
    events = await _collect(service, "Thủ tục ly hôn hiện nay thế nào?")
    tokens = [e.text for e in events if isinstance(e, LegalQAToken)]
    assert len(tokens) == 1 and "Không tìm thấy" in tokens[0]
    assert llm.stream_calls == []
    assert search.calls[0]["min_score"] == 0.8


async def test_compare_marks_removed_and_added_provisions() -> None:
    repealed = make_hit(f"{LAW}#D9", "Điều 9. Quy định cũ.", date(2024, 8, 1), JULY)
    added = make_hit(f"{LAW}#D10", "Điều 10. Quy định mới.", JULY)
    service, llm, _, _ = _service(hits=(repealed, added))
    events = await _collect(service, "So sánh quy định ngày 01/01/2026 và ngày 01/08/2026")
    roles = {c["legal"]["provision_key"]: c["legal"]["role"] for c in events[-1].citations}
    assert roles == {f"{LAW}#D9": "removed", f"{LAW}#D10": "added"}
    user = llm.stream_calls[0][1]["content"]
    assert "(Không còn hiệu lực ở thời điểm sau)" in user
    assert "(Quy định mới, chưa có ở thời điểm trước)" in user
