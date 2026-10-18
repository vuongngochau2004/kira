from datetime import date

import pytest

from src.modules.legal.application.errors import InvalidLegalDocumentState
from src.modules.legal.application.publish_document import PublishLegalDocument
from src.modules.legal.application.records import CandidateStatus, LegalDocumentStatus
from src.modules.legal.domain.models import RelationType
from tests.legal_fakes import (
    FakeLegalGraph,
    FakeSearchIndex,
    InMemoryLegalRepository,
    make_candidate,
    make_document,
)

BASE = "31/2024/QH15"
AMENDING = "99/2026/QH15"
BASE_TEXT = """Luật số: 31/2024/QH15
Căn cứ Hiến pháp;
Điều 3. Quyền của Nhà nước
1. Quyết định quy hoạch sử dụng đất.
2. Quyết định giá đất.
Điều 4. Giải thích từ ngữ
1. Định nghĩa cũ A.
"""
AMENDING_TEXT = """Luật số: 99/2026/QH15
Điều 1. Sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15
1. Sửa đổi, bổ sung khoản 1 Điều 3 như sau:
“1. Quyết định quy hoạch và kế hoạch sử dụng đất.”
Điều 2. Hiệu lực thi hành
Luật này có hiệu lực từ ngày 01 tháng 7 năm 2026.
"""
JULY_2026 = date(2026, 7, 1)


async def _setup(
    base_status: LegalDocumentStatus = LegalDocumentStatus.PUBLISHED,
    amending_status: LegalDocumentStatus = LegalDocumentStatus.IN_REVIEW,
):
    repository = InMemoryLegalRepository()
    base = make_document(BASE, status=base_status, text=BASE_TEXT)
    amending = make_document(
        AMENDING, status=amending_status, effective_date=JULY_2026, text=AMENDING_TEXT
    )
    await repository.create_document(base)
    await repository.create_document(amending)
    graph, index = FakeLegalGraph(), FakeSearchIndex()
    return PublishLegalDocument(repository, graph, index), repository, graph, index, base, amending


def _amend(amending, ref: str, text: str, **kwargs):
    return make_candidate(
        amending,
        RelationType.AMENDS,
        BASE,
        ref=ref,
        new_text=text,
        source_key=f"{AMENDING}#D1.K1",
        **kwargs,
    )


async def test_publish_base_document_writes_one_open_version_per_provision() -> None:
    service, repository, graph, index, base, _ = await _setup(
        base_status=LegalDocumentStatus.IN_REVIEW
    )
    result = (await service.execute(base.id)).document

    assert result.status is LegalDocumentStatus.PUBLISHED
    assert result.published_at is not None
    assert graph.calls[:3] == ["ensure_schema", "upsert_document", "upsert_provisions"]
    assert set(graph.timelines) == {
        f"{BASE}#D3",
        f"{BASE}#D3.K1",
        f"{BASE}#D3.K2",
        f"{BASE}#D4",
        f"{BASE}#D4.K1",
    }
    for versions in graph.timelines.values():
        assert [(v.valid_from, v.valid_to) for v in versions] == [(date(2024, 8, 1), None)]
    assert set(index.versions) == set(graph.timelines)
    assert index.labels[f"{BASE}#D3.K1"] == "Khoản 1"
    assert graph.provisions[f"{BASE}#D3.K1"].parent_key == f"{BASE}#D3"
    assert graph.relations[BASE] == []
    stored = await repository.get_document(base.id)
    assert stored is not None and stored.status is LegalDocumentStatus.PUBLISHED


async def test_publish_amending_document_rebuilds_target_timeline() -> None:
    service, repository, graph, index, _, amending = await _setup()
    candidate = _amend(amending, "D3.K1", "1. Quyết định quy hoạch và kế hoạch sử dụng đất.")
    await repository.save_candidate(candidate)

    await service.execute(amending.id)

    versions = graph.timelines[f"{BASE}#D3.K1"]
    assert [v.text for v in versions] == [
        "1. Quyết định quy hoạch sử dụng đất.",
        "1. Quyết định quy hoạch và kế hoạch sử dụng đất.",
    ]
    assert versions[0].valid_to == JULY_2026
    assert versions[1].introduced_by == f"{AMENDING}#D1.K1"
    assert f"{BASE}#D3.K2" not in graph.timelines
    assert len(index.versions[f"{BASE}#D3.K1"]) == 2
    [relation] = graph.relations[AMENDING]
    assert relation.type == "AMENDS"
    assert relation.source_key == f"{AMENDING}#D1.K1"
    assert relation.target_key == f"{BASE}#D3.K1"
    assert relation.review_id == str(candidate.id)


async def test_amendment_from_unpublished_document_is_ignored_on_target_republish() -> None:
    service, repository, graph, _, base, amending = await _setup()
    await repository.save_candidate(_amend(amending, "D3.K1", "1. Nội dung mới."))

    await service.execute(base.id)

    assert len(graph.timelines[f"{BASE}#D3.K1"]) == 1


async def test_timeline_conflict_fails_without_writes() -> None:
    service, repository, graph, index, _, amending = await _setup()
    first = _amend(amending, "D3.K1", "1. Một.")
    second = _amend(amending, "D3.K1", "1. Hai.")
    await repository.save_candidate(first)
    await repository.save_candidate(second)

    result = (await service.execute(amending.id)).document

    assert result.status is LegalDocumentStatus.FAILED
    assert "same_effective_date" in (result.error_detail or "")
    assert graph.calls == []
    assert index.versions == {}


async def test_document_replacement_terminates_every_target_provision() -> None:
    service, repository, graph, _, _, amending = await _setup()
    await repository.save_candidate(
        make_candidate(amending, RelationType.REPLACES, BASE, source_key=f"{AMENDING}#D2")
    )

    await service.execute(amending.id)

    base_keys = [key for key in graph.timelines if key.startswith(f"{BASE}#")]
    assert len(base_keys) == 5
    for key in base_keys:
        assert graph.timelines[key][-1].valid_to == JULY_2026
    [relation] = graph.relations[AMENDING]
    assert relation.type == "REPLACES"
    assert relation.source_key is None
    assert relation.target_key is None


async def test_inserted_provision_gets_node_and_timeline() -> None:
    service, repository, graph, index, _, amending = await _setup()
    await repository.save_candidate(_amend(amending, "D3a", "Điều 3a. Quyền định giá đất"))

    await service.execute(amending.id)

    node = graph.provisions[f"{BASE}#D3a"]
    assert (node.level, node.label, node.parent_key, node.document_number) == (
        "article",
        "Điều 3a",
        None,
        BASE,
    )
    [version] = graph.timelines[f"{BASE}#D3a"]
    assert (version.valid_from, version.valid_to) == (JULY_2026, None)
    assert index.labels[f"{BASE}#D3a"] == "Điều 3a"


async def test_article_amendment_closes_its_clauses() -> None:
    service, repository, graph, _, _, amending = await _setup()
    await repository.save_candidate(
        _amend(amending, "D4", "Điều 4. Giải thích từ ngữ\n1. Định nghĩa mới A.")
    )

    await service.execute(amending.id)

    assert len(graph.timelines[f"{BASE}#D4"]) == 2
    [clause_version] = graph.timelines[f"{BASE}#D4.K1"]
    assert clause_version.valid_to == JULY_2026


async def test_rejected_amendment_is_rolled_back_on_republish() -> None:
    service, repository, graph, _, _, amending = await _setup(
        amending_status=LegalDocumentStatus.PUBLISHED
    )
    await repository.save_candidate(
        _amend(amending, "D3.K1", "1. Nội dung mới.", status=CandidateStatus.REJECTED)
    )

    await service.execute(amending.id)

    [version] = graph.timelines[f"{BASE}#D3.K1"]
    assert version.valid_to is None
    assert graph.relations[AMENDING] == []


async def test_relations_to_unpublished_targets_are_skipped() -> None:
    service, repository, graph, _, _, amending = await _setup()
    decree = make_document("10/2026/NĐ-CP", status=LegalDocumentStatus.IN_REVIEW, doc_type="decree")
    await repository.create_document(decree)
    await repository.save_candidate(
        make_candidate(amending, RelationType.GUIDES, decree.metadata.number)
    )
    await repository.save_candidate(make_candidate(amending, RelationType.BASED_ON, BASE))
    await repository.save_candidate(
        make_candidate(amending, RelationType.BASED_ON, BASE, status=CandidateStatus.PENDING)
    )

    await service.execute(amending.id)

    assert [(r.type, r.target_number) for r in graph.relations[AMENDING]] == [("BASED_ON", BASE)]


async def test_graph_failure_marks_document_failed() -> None:
    service, _, graph, _, base, _ = await _setup(base_status=LegalDocumentStatus.IN_REVIEW)
    graph.fail_on = "replace_provision_timeline"
    result = (await service.execute(base.id)).document
    assert result.status is LegalDocumentStatus.FAILED
    assert "replace_provision_timeline failed" in (result.error_detail or "")


async def test_unprocessed_document_cannot_be_published() -> None:
    service, repository, _, _, _, _ = await _setup()
    uploaded = make_document("7/2026/QH15", status=LegalDocumentStatus.UPLOADED)
    await repository.create_document(uploaded)
    with pytest.raises(InvalidLegalDocumentState):
        await service.execute(uploaded.id)


async def test_rejected_insertion_is_removed_on_republish() -> None:
    service, repository, graph, index, _, amending = await _setup()
    candidate = _amend(amending, "D3.K9", "9. Mới.")
    await repository.save_candidate(candidate)
    await service.execute(amending.id)
    assert graph.timelines[f"{BASE}#D3.K9"]
    candidate.status = CandidateStatus.REJECTED
    await repository.save_candidate(candidate)

    await service.execute(amending.id)

    assert f"{BASE}#D3.K9" in graph.deleted_provisions
    assert f"{BASE}#D3.K9" not in graph.provisions
    assert index.versions[f"{BASE}#D3.K9"] == []


async def test_edited_target_rolls_back_previous_target() -> None:
    service, repository, graph, _, _, amending = await _setup()
    candidate = _amend(amending, "D3.K1", "1. Mới.")
    await repository.save_candidate(candidate)
    await service.execute(amending.id)
    candidate.target_provision_ref = "D3.K2"
    candidate.new_text = "2. Mới."
    await repository.save_candidate(candidate)

    await service.execute(amending.id)

    assert len(graph.timelines[f"{BASE}#D3.K1"]) == 1
    assert graph.timelines[f"{BASE}#D3.K2"][-1].text == "2. Mới."


async def test_rollback_applies_while_target_is_failed() -> None:
    service, repository, graph, _, base, amending = await _setup()
    candidate = _amend(amending, "D3.K1", "1. Mới.")
    await repository.save_candidate(candidate)
    await service.execute(amending.id)
    base.status = LegalDocumentStatus.FAILED  # a later republish failed; its graph data remains
    await repository.save_document(base)
    candidate.status = CandidateStatus.REJECTED
    await repository.save_candidate(candidate)

    await service.execute(amending.id)

    assert len(graph.timelines[f"{BASE}#D3.K1"]) == 1


async def test_publish_takes_corpus_lock_before_planning() -> None:
    service, repository, _, _, base, _ = await _setup(base_status=LegalDocumentStatus.IN_REVIEW)
    await service.execute(base.id)
    events = repository.events
    assert events.index("acquire_publish_lock") < events.index("list_candidates")


async def test_first_publish_of_target_requests_republish_of_its_amenders() -> None:
    service, repository, _, _, base, amending = await _setup(
        base_status=LegalDocumentStatus.IN_REVIEW,
        amending_status=LegalDocumentStatus.PUBLISHED,
    )
    await repository.save_candidate(_amend(amending, "D3.K1", "1. Mới."))

    first = await service.execute(base.id)
    again = await service.execute(base.id)

    assert first.republish_document_ids == [amending.id]
    assert again.republish_document_ids == []
