from src.modules.legal.domain.extraction import extract_rule_candidates, find_document_numbers
from src.modules.legal.domain.models import RelationType
from src.modules.legal.domain.parser import parse_legal_structure

AMENDING_LAW = """Luật số: 99/2026/QH15
Căn cứ Hiến pháp;
Căn cứ Luật Đất đai số 31/2024/QH15 và Luật số 99/2026/QH15;
Điều 1. Sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15
1. Sửa đổi, bổ sung khoản 1 Điều 3 như sau:
“1. Quyết định quy hoạch và kế hoạch sử dụng đất.”
2. Bổ sung Điều 3a vào sau Điều 3 như sau:
“Điều 3a. Quyền định giá đất
1. Nhà nước quyết định giá đất.”
Điều 2. Hiệu lực thi hành
1. Luật này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2026.
2. Luật này thay thế Luật Đất đai số 45/2013/QH13.
3. Luật Nhà ở số 65/2014/QH13 hết hiệu lực kể từ ngày Luật này có hiệu lực.
4. Bãi bỏ khoản 3 Điều 5 và Điều 7 của Nghị định số 43/2014/NĐ-CP.
5. Thay thế cụm từ “cơ quan” bằng cụm từ “cơ quan nhà nước” tại Luật số 12/2020/QH14.
"""

DECREE = """Nghị định số: 10/2026/NĐ-CP
Căn cứ Luật Đất đai số 31/2024/QH15;
Điều 1. Phạm vi điều chỉnh
Nghị định này quy định chi tiết một số điều của Luật Đất đai số 31/2024/QH15.
"""

OWN = "99/2026/QH15"


def _drafts(text: str, number: str):
    return extract_rule_candidates(parse_legal_structure(text, number), number)


def _of_type(drafts, relation_type):
    return [draft for draft in drafts if draft.type is relation_type]


def test_find_document_numbers_formats() -> None:
    text = "Luật 45/2024/QH15, Nghị định 100/2015/NĐ-CP, Thông tư 15/2025/TT-BTC; ngày 1/7/2026"
    assert find_document_numbers(text) == ["45/2024/QH15", "100/2015/NĐ-CP", "15/2025/TT-BTC"]


def test_based_on_from_preamble_excludes_own_number() -> None:
    based_on = _of_type(_drafts(AMENDING_LAW, OWN), RelationType.BASED_ON)
    assert [d.target_number for d in based_on] == ["31/2024/QH15"]
    assert based_on[0].source_provision_key is None
    assert based_on[0].evidence_text.startswith("Căn cứ Luật Đất đai")
    assert based_on[0].confidence == 0.95


def test_no_relation_targets_own_number() -> None:
    assert all(d.target_number != OWN for d in _drafts(AMENDING_LAW, OWN))


def test_replaces_and_expiry() -> None:
    replaces = _of_type(_drafts(AMENDING_LAW, OWN), RelationType.REPLACES)
    assert {(d.target_number, d.confidence) for d in replaces} == {
        ("45/2013/QH13", 0.9),
        ("65/2014/QH13", 0.85),
    }
    assert all(d.target_provision_ref is None for d in replaces)
    assert {d.source_provision_key for d in replaces} == {f"{OWN}#D2.K2", f"{OWN}#D2.K3"}


def test_word_replacement_is_not_a_document_replacement() -> None:
    targets = {d.target_number for d in _drafts(AMENDING_LAW, OWN)}
    assert "12/2020/QH14" not in targets


def test_repeals_per_provision_ref() -> None:
    repeals = _of_type(_drafts(AMENDING_LAW, OWN), RelationType.REPEALS)
    assert [(d.target_number, d.target_provision_ref) for d in repeals] == [
        ("43/2014/NĐ-CP", "D5.K3"),
        ("43/2014/NĐ-CP", "D7"),
    ]


def test_amendments_carry_quoted_new_text() -> None:
    amends = _of_type(_drafts(AMENDING_LAW, OWN), RelationType.AMENDS)
    assert [(d.target_number, d.target_provision_ref) for d in amends] == [
        ("31/2024/QH15", "D3.K1"),
        ("31/2024/QH15", "D3a"),
    ]
    assert amends[0].new_text == "1. Quyết định quy hoạch và kế hoạch sử dụng đất."
    assert amends[1].new_text == "Điều 3a. Quyền định giá đất\n1. Nhà nước quyết định giá đất."
    assert amends[0].source_provision_key == f"{OWN}#D1.K1"
    assert amends[0].evidence_text == "1. Sửa đổi, bổ sung khoản 1 Điều 3 như sau:"
    assert amends[0].confidence == 0.7


def test_guides_document_level() -> None:
    drafts = _drafts(DECREE, "10/2026/NĐ-CP")
    guides = _of_type(drafts, RelationType.GUIDES)
    assert [(d.target_number, d.target_provision_ref) for d in guides] == [("31/2024/QH15", None)]
    assert guides[0].source_provision_key == "10/2026/NĐ-CP#D1"


def test_results_are_deduplicated() -> None:
    drafts = _drafts(AMENDING_LAW, OWN)
    keys = [
        (d.type, d.source_provision_key, d.target_number, d.target_provision_ref, d.new_text)
        for d in drafts
    ]
    assert len(keys) == len(set(keys))


BROKEN_SECOND_QUOTE = """Luật số: 50/2026/QH15
Điều 1. Sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15
1. Sửa đổi, bổ sung Điều 4 như sau:
“Điều 4. Giải thích từ ngữ
1. Định nghĩa A.
2. Định nghĩa B.”
2. Sửa đổi khoản 1 Điều 9 như sau:
“1. Nội dung mới chưa đóng ngoặc
Điều 2. Hiệu lực thi hành
Luật này có hiệu lực từ ngày 01 tháng 7 năm 2026.
"""

INSERTIONS_AND_LISTS = """Luật số: 60/2026/QH15
Điều 1. Sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15
1. Bổ sung điểm c vào khoản 1 Điều 7 như sau:
“c) Nội dung điểm c.”
2. Bổ sung khoản 3a vào sau khoản 3 Điều 10 như sau:
“3a. Nội dung khoản 3a.”
3. Sửa đổi khoản 2 và khoản 3 Điều 5 như sau:
“2. Nội dung hai.
3. Nội dung ba.”
4. Bãi bỏ các điểm a và b khoản 2 Điều 5 của Nghị định số 43/2014/NĐ-CP.
"""


def test_correct_amendment_survives_a_broken_quote_elsewhere() -> None:
    amends = _of_type(_drafts(BROKEN_SECOND_QUOTE, "50/2026/QH15"), RelationType.AMENDS)
    assert [d.target_provision_ref for d in amends] == ["D4"]
    assert amends[0].new_text == "Điều 4. Giải thích từ ngữ\n1. Định nghĩa A.\n2. Định nghĩa B."


def test_insertions_target_the_new_provision() -> None:
    amends = _of_type(_drafts(INSERTIONS_AND_LISTS, "60/2026/QH15"), RelationType.AMENDS)
    assert [(d.target_number, d.target_provision_ref, d.new_text) for d in amends] == [
        ("31/2024/QH15", "D7.K1.c", "c) Nội dung điểm c."),
        ("31/2024/QH15", "D10.K3a", "3a. Nội dung khoản 3a."),
    ]


def test_multi_target_amendment_is_left_for_llm() -> None:
    amends = _of_type(_drafts(INSERTIONS_AND_LISTS, "60/2026/QH15"), RelationType.AMENDS)
    assert all(d.target_provision_ref not in {"D5.K2", "D5.K3"} for d in amends)


def test_repeal_lists_produce_one_candidate_per_item() -> None:
    repeals = _of_type(_drafts(INSERTIONS_AND_LISTS, "60/2026/QH15"), RelationType.REPEALS)
    assert [(d.target_number, d.target_provision_ref) for d in repeals] == [
        ("43/2014/NĐ-CP", "D5.K2.a"),
        ("43/2014/NĐ-CP", "D5.K2.b"),
    ]
