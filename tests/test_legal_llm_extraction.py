import pytest

from src.modules.legal.domain.extraction.llm import (
    LLM_AMENDMENT_CONFIDENCE,
    build_amendment_messages,
    parse_amendment_response,
    select_amendment_provisions,
)
from src.modules.legal.domain.models import ProvisionLevel, RelationType
from src.modules.legal.domain.parser import parse_legal_structure
from src.modules.legal.domain.provision_key import (
    describe_provision_ref,
    is_valid_provision_ref,
    split_provision_key,
)

OWN = "99/2026/QH15"
TEXT = """Điều 1. Sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15
1. Sửa đổi, bổ sung khoản 1 Điều 3 như sau:
“1. Nội dung do rule xử lý.”
2. Sửa đổi khoản 2 như sau:
“2. Nội dung mới về giá đất.”
3. Quy định chuyển tiếp không có trích dẫn.
Điều 2. Hiệu lực thi hành
Luật này có hiệu lực từ ngày 01 tháng 7 năm 2026.
"""


def _result():
    return parse_legal_structure(TEXT, OWN)


def test_provision_ref_helpers() -> None:
    assert is_valid_provision_ref("D12.K3.a")
    assert is_valid_provision_ref("D3a")
    assert is_valid_provision_ref("D10.K3a")
    assert not is_valid_provision_ref("D12.k3")
    assert not is_valid_provision_ref("Điều 12")
    assert split_provision_key("31/2024/QH15#D3.K1") == ("31/2024/QH15", "D3.K1")
    with pytest.raises(ValueError):
        split_provision_key("31/2024/QH15")
    assert describe_provision_ref("D3a") == (ProvisionLevel.ARTICLE, "Điều 3a", None)
    assert describe_provision_ref("D10.K3a") == (ProvisionLevel.CLAUSE, "Khoản 3a", "D10")
    assert describe_provision_ref("D7.K1.c") == (ProvisionLevel.POINT, "Điểm c", "D7.K1")


def test_select_skips_rule_covered_and_non_amendment_provisions() -> None:
    selected = select_amendment_provisions(_result(), {f"{OWN}#D1.K1"}, limit=10)
    assert [p.provision_key for p in selected] == [f"{OWN}#D1.K2"]
    assert select_amendment_provisions(_result(), set(), limit=1)[0].provision_key == f"{OWN}#D1.K1"


def test_messages_include_parent_context_and_keys() -> None:
    result = _result()
    provisions = select_amendment_provisions(result, {f"{OWN}#D1.K1"}, limit=10)
    messages = build_amendment_messages(result, provisions, OWN)
    assert messages[0]["role"] == "system"
    assert '"amendments"' in messages[0]["content"]
    user = messages[1]["content"]
    assert f"### {OWN}#D1.K2" in user
    assert "Context: Điều 1. Sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15" in user


def _provisions():
    result = _result()
    return select_amendment_provisions(result, {f"{OWN}#D1.K1"}, limit=10)


def _item(**overrides):
    item = {
        "source_provision_key": f"{OWN}#D1.K2",
        "target_number": "31/2024/QH15",
        "target_provision_ref": "D3.K2",
        "new_text": "“2. Nội dung mới về giá đất.”",
    }
    item.update(overrides)
    return item


def test_valid_item_becomes_llm_draft() -> None:
    drafts = parse_amendment_response({"amendments": [_item()]}, _provisions(), OWN)
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.type is RelationType.AMENDS
    assert draft.extractor == "llm"
    assert draft.confidence == LLM_AMENDMENT_CONFIDENCE
    assert draft.new_text == "2. Nội dung mới về giá đất."
    assert draft.target_provision_ref == "D3.K2"
    assert draft.evidence_text == "2. Sửa đổi khoản 2 như sau:"


@pytest.mark.parametrize(
    "bad",
    [
        {"new_text": "2. Nội dung bịa đặt không có trong văn bản."},
        {"target_provision_ref": "Điều 3 khoản 2"},
        {"target_number": OWN},
        {"target_number": "luật đất đai"},
        {"source_provision_key": f"{OWN}#D9"},
        {"new_text": "   "},
    ],
)
def test_invalid_items_are_dropped(bad: dict) -> None:
    assert parse_amendment_response({"amendments": [_item(**bad)]}, _provisions(), OWN) == []


def test_missing_amendments_list_raises() -> None:
    with pytest.raises(ValueError):
        parse_amendment_response({}, _provisions(), OWN)
    with pytest.raises(ValueError):
        parse_amendment_response({"amendments": "none"}, _provisions(), OWN)
