from datetime import date

from src.modules.legal.domain.prompts.legal_qa import (
    GRAPH_UNAVAILABLE_NOTICE,
    applied_date_sentence,
    build_legal_qa_messages,
    citation_payload,
    not_found_message,
    source_block,
)
from src.modules.legal.domain.qa import LegalSource
from src.modules.legal.domain.temporal import TemporalQuery
from tests.legal_fakes import make_hit

SINGLE = TemporalQuery("single", (date(2026, 10, 15),), "present tense", "rule")
COMPARE = TemporalQuery("compare", (date(2026, 6, 30), date(2026, 7, 1)), "x", "rule")
HIT = make_hit("31/2024/QH15#D12.K3", "3. Nội dung khoản 3.", date(2024, 8, 1))


def test_header_matches_spec_format() -> None:
    block = source_block(1, LegalSource(hit=HIT))
    assert block.splitlines()[0] == (
        "[1] Khoản 3 — Luật Đất đai số 31/2024/QH15 — hiệu lực 01/08/2024 → nay"
    )
    assert block.endswith("3. Nội dung khoản 3.")


def test_block_notes_parent_provenance_and_later_change() -> None:
    source = LegalSource(
        hit=HIT,
        role="after",
        parent_label="Điều 12",
        parent_text="Điều 12. Quyền sử dụng đất",
        amended_after=date(2027, 1, 1),
        introduced_by_number="99/2026/QH15",
        introduced_by_title="Luật sửa đổi Luật Đất đai",
    )
    block = source_block(2, source)
    assert "(Quy định sau thay đổi)" in block
    assert "Thuộc Điều 12: Điều 12. Quyền sử dụng đất" in block
    assert "được sửa đổi bởi Luật sửa đổi Luật Đất đai số 99/2026/QH15" in block
    assert "đã được sửa đổi từ ngày 01/01/2027" in block


def test_applied_sentences() -> None:
    assert applied_date_sentence(SINGLE) == "Áp dụng tại ngày 15/10/2026."
    assert (
        applied_date_sentence(COMPARE) == "So sánh quy định tại ngày 30/06/2026 và ngày 01/07/2026."
    )
    assert not_found_message(SINGLE).startswith("Áp dụng tại ngày 15/10/2026. Không tìm thấy")


def test_messages_contain_sources_notices_and_question() -> None:
    messages = build_legal_qa_messages(
        "Khoản 3 quy định gì?", SINGLE, [LegalSource(hit=HIT)], [GRAPH_UNAVAILABLE_NOTICE]
    )
    assert messages[0]["role"] == "system"
    assert "[n]" in messages[0]["content"]
    user = messages[1]["content"]
    assert user.startswith("NGÀY ÁP DỤNG: Áp dụng tại ngày 15/10/2026.")
    assert "[1] Khoản 3 — Luật Đất đai số 31/2024/QH15" in user
    assert GRAPH_UNAVAILABLE_NOTICE in user
    assert user.endswith("CÂU HỎI: Khoản 3 quy định gì?")


def test_citation_payload_has_legal_data_and_no_document_id() -> None:
    source = LegalSource(hit=HIT, amended_after=date(2027, 1, 1))
    payload = citation_payload(source, snippet_length=10)
    assert "document_id" not in payload
    assert payload["filename"] == "Khoản 3 — Luật Đất đai (31/2024/QH15)"
    assert payload["text"] == "3. Nội dun"
    assert payload["chunk_id"] == HIT.version_id
    assert payload["legal"] == {
        "number": "31/2024/QH15",
        "doc_type": "law",
        "provision_key": "31/2024/QH15#D12.K3",
        "label": "Khoản 3",
        "title": "Luật Đất đai",
        "valid_from": "2024-08-01",
        "valid_to": None,
        "amended_after": "2027-01-01",
        "role": "primary",
    }
