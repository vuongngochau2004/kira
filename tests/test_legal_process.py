import json
from datetime import date

import pytest

from src.modules.legal.application.errors import InvalidLegalDocumentState
from src.modules.legal.application.process_document import ProcessLegalDocument
from src.modules.legal.application.records import (
    AUTO_APPROVED_NOTE,
    LLM_EXTRACTION_INCOMPLETE_FLAG,
    CandidateStatus,
    LegalDocumentStatus,
)
from src.modules.legal.domain.models import RelationType
from tests.legal_fakes import (
    FakeLLM,
    FakeStorage,
    FakeTextExtractor,
    InMemoryLegalRepository,
    make_candidate,
    make_document,
)

OWN = "99/2026/QH15"
AMENDING_LAW = """Luật số: 99/2026/QH15
Căn cứ Hiến pháp;
Căn cứ Luật Đất đai số 31/2024/QH15;
Điều 1. Sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15
1. Sửa đổi, bổ sung khoản 1 Điều 3 như sau:
“1. Quyết định quy hoạch và kế hoạch sử dụng đất.”
2. Sửa đổi khoản 2 như sau:
“2. Nội dung mới về giá đất.”
Điều 2. Hiệu lực thi hành
1. Luật này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2026.
2. Luật này thay thế Luật Đất đai số 45/2013/QH13.
"""

LLM_OK = json.dumps(
    {
        "amendments": [
            {
                "source_provision_key": f"{OWN}#D1.K2",
                "target_number": "31/2024/QH15",
                "target_provision_ref": "D3.K2",
                "new_text": "2. Nội dung mới về giá đất.",
            }
        ]
    }
)


async def _setup(text: str = AMENDING_LAW, *llm_responses: str | Exception):
    repository = InMemoryLegalRepository()
    storage = FakeStorage()
    target = make_document("31/2024/QH15")
    await repository.create_document(target)
    document = make_document(
        OWN,
        status=LegalDocumentStatus.UPLOADED,
        effective_date=date(2026, 7, 1),
    )
    await repository.create_document(document)
    storage.objects[document.file_key] = text.encode("utf-8")
    llm = FakeLLM(*llm_responses)
    service = ProcessLegalDocument(
        repository,
        storage,
        FakeTextExtractor(),
        llm,
        auto_approve_types=["BASED_ON", "AMENDS"],
        llm_max_provisions=10,
    )
    return service, repository, document, llm


async def test_process_creates_candidates_and_moves_to_review() -> None:
    service, repository, document, llm = await _setup(AMENDING_LAW, LLM_OK)
    result = await service.execute(document.id)

    assert result.status is LegalDocumentStatus.IN_REVIEW
    assert result.warnings == []
    assert result.parsed_structure is not None
    assert result.parsed_structure[0]["provision_key"] == f"{OWN}#D1"

    candidates = await repository.list_candidates(document.id)
    by_type = {(c.type, c.target_provision_ref): c for c in candidates}
    based_on = by_type[(RelationType.BASED_ON, None)]
    assert based_on.status is CandidateStatus.APPROVED
    assert based_on.review_note == AUTO_APPROVED_NOTE
    rule_amend = by_type[(RelationType.AMENDS, "D3.K1")]
    assert rule_amend.status is CandidateStatus.PENDING  # AMENDS is never auto-approved
    assert rule_amend.effective_date == date(2026, 7, 1)
    llm_amend = by_type[(RelationType.AMENDS, "D3.K2")]
    assert llm_amend.extractor == "llm"
    replaces = by_type[(RelationType.REPLACES, None)]
    assert replaces.target_number == "45/2013/QH13"
    assert replaces.status is CandidateStatus.UNRESOLVED_TARGET
    assert len(llm.calls) == 1


async def test_llm_failure_keeps_rule_candidates_and_flags_document() -> None:
    service, repository, document, llm = await _setup(
        AMENDING_LAW, RuntimeError("timeout"), "not json at all"
    )
    result = await service.execute(document.id)
    assert result.status is LegalDocumentStatus.IN_REVIEW
    assert result.warnings == [LLM_EXTRACTION_INCOMPLETE_FLAG]
    assert len(llm.calls) == 2
    types = {c.type for c in await repository.list_candidates(document.id)}
    assert RelationType.AMENDS in types


async def test_no_llm_call_when_rules_cover_everything() -> None:
    text = AMENDING_LAW.replace("2. Sửa đổi khoản 2 như sau:\n“2. Nội dung mới về giá đất.”\n", "")
    service, _, document, llm = await _setup(text)
    await service.execute(document.id)
    assert llm.calls == []


async def test_parse_failure_marks_document_failed() -> None:
    service, repository, document, _ = await _setup("Chỉ là một đoạn văn bản.")
    result = await service.execute(document.id)
    assert result.status is LegalDocumentStatus.FAILED
    assert "No articles found" in (result.error_detail or "")
    assert await repository.list_candidates(document.id) == []


async def test_empty_file_marks_document_failed() -> None:
    service, _, document, _ = await _setup("   ")
    result = await service.execute(document.id)
    assert result.status is LegalDocumentStatus.FAILED
    assert result.error_detail == "No text extracted"


async def test_waiting_candidates_of_other_documents_are_resolved() -> None:
    service, repository, document, _ = await _setup(AMENDING_LAW, LLM_OK)
    later_law = make_document("50/2027/QH15", status=LegalDocumentStatus.IN_REVIEW)
    await repository.create_document(later_law)
    waiting = make_candidate(
        later_law,
        RelationType.AMENDS,
        OWN,
        ref="D2.K1",
        new_text="1. Mới.",
        status=CandidateStatus.UNRESOLVED_TARGET,
    )
    await repository.save_candidate(waiting)

    await service.execute(document.id)

    resolved = await repository.get_candidate(waiting.id)
    assert resolved is not None
    assert resolved.status is CandidateStatus.PENDING


async def test_published_document_cannot_be_reprocessed() -> None:
    service, repository, document, _ = await _setup()
    document.status = LegalDocumentStatus.PUBLISHED
    await repository.save_document(document)
    with pytest.raises(InvalidLegalDocumentState):
        await service.execute(document.id)
