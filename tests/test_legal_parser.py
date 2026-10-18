import pytest

from src.modules.legal.domain.errors import LegalParseError
from src.modules.legal.domain.models import ProvisionLevel
from src.modules.legal.domain.parser import (
    DUPLICATE_PROVISION_KEY_WARNING,
    UNBALANCED_QUOTES_WARNING,
    parse_legal_structure,
)

SAMPLE_LAW = """<!-- page 1 -->
QUỐC HỘI
Luật số: 31/2024/QH15

LUẬT ĐẤT ĐAI

Căn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam;
Căn cứ Luật Ban hành văn bản quy phạm pháp luật số 80/2015/QH13;

Chương I
QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Luật này quy định về chế độ sở hữu đất đai.

Điều 2. Giải thích từ ngữ
Trong Luật này, các từ ngữ dưới đây được hiểu như sau:
1. Bản đồ địa chính là bản đồ thể hiện các thửa đất.
2. Chủ sử dụng đất bao gồm:
a) Cá nhân trong nước;
b) Tổ chức kinh tế.
<!-- page 2 -->
Chương II
QUYỀN CỦA NHÀ NƯỚC

**Điều 3. Quyền của Nhà nước**
1. Quyết định quy hoạch sử dụng đất.
Điều 3 được áp dụng thống nhất.

Phụ lục I
Điều 1. Mẫu đơn không phải điều khoản
"""

AMENDING_LAW = """Luật số: 99/2026/QH15
Căn cứ Hiến pháp;
Điều 1. Sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15
1. Sửa đổi, bổ sung khoản 1 Điều 3 như sau:
“1. Quyết định quy hoạch và kế hoạch sử dụng đất.”
2. Bổ sung Điều 3a vào sau Điều 3 như sau:
“Điều 3a. Quyền định giá đất
1. Nhà nước quyết định giá đất.”
Điều 2. Hiệu lực thi hành
Luật này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2026.
"""

N = "31/2024/QH15"


def _by_key(text: str, number: str):
    return {p.provision_key: p for p in parse_legal_structure(text, number).provisions}


def test_parses_article_clause_point_tree() -> None:
    provisions = _by_key(SAMPLE_LAW, N)
    assert list(provisions) == [
        f"{N}#D1",
        f"{N}#D2",
        f"{N}#D2.K1",
        f"{N}#D2.K2",
        f"{N}#D2.K2.a",
        f"{N}#D2.K2.b",
        f"{N}#D3",
        f"{N}#D3.K1",
    ]
    assert provisions[f"{N}#D2.K2.a"].level is ProvisionLevel.POINT
    assert provisions[f"{N}#D2.K2.a"].parent_key == f"{N}#D2.K2"
    assert provisions[f"{N}#D2.K2"].parent_key == f"{N}#D2"
    assert provisions[f"{N}#D2"].parent_key is None


def test_article_text_is_own_text_only() -> None:
    article = _by_key(SAMPLE_LAW, N)[f"{N}#D2"]
    assert article.label == "Điều 2"
    assert article.heading == "Giải thích từ ngữ"
    assert article.text == (
        "Điều 2. Giải thích từ ngữ\nTrong Luật này, các từ ngữ dưới đây được hiểu như sau:"
    )


def test_bold_heading_and_body_line_starting_with_dieu() -> None:
    provisions = _by_key(SAMPLE_LAW, N)
    assert provisions[f"{N}#D3"].heading == "Quyền của Nhà nước"
    assert provisions[f"{N}#D3.K1"].text == (
        "1. Quyết định quy hoạch sử dụng đất.\nĐiều 3 được áp dụng thống nhất."
    )


def test_pages_and_chapters() -> None:
    provisions = _by_key(SAMPLE_LAW, N)
    assert provisions[f"{N}#D1"].page == 1
    assert provisions[f"{N}#D3"].page == 2
    assert provisions[f"{N}#D1"].chapter_label == "Chương I. QUY ĐỊNH CHUNG"
    assert provisions[f"{N}#D3"].chapter_label == "Chương II. QUYỀN CỦA NHÀ NƯỚC"


def test_preamble_keeps_can_cu_lines_and_appendix_is_ignored() -> None:
    result = parse_legal_structure(SAMPLE_LAW, N)
    assert "Căn cứ Luật Ban hành văn bản quy phạm pháp luật số 80/2015/QH13;" in result.preamble
    assert "Mẫu đơn" not in "".join(p.text for p in result.provisions)
    assert result.warnings == ()


def test_quoted_amendment_content_stays_inside_clause() -> None:
    number = "99/2026/QH15"
    provisions = _by_key(AMENDING_LAW, number)
    assert list(provisions) == [
        f"{number}#D1",
        f"{number}#D1.K1",
        f"{number}#D1.K2",
        f"{number}#D2",
    ]
    clause_two = provisions[f"{number}#D1.K2"].text
    assert "“Điều 3a. Quyền định giá đất" in clause_two
    assert "1. Nhà nước quyết định giá đất.”" in clause_two


def test_unbalanced_quote_does_not_swallow_following_articles() -> None:
    broken = AMENDING_LAW.replace(
        "1. Nhà nước quyết định giá đất.”", "1. Nhà nước quyết định giá đất."
    )
    result = parse_legal_structure(broken, "99/2026/QH15")
    keys = [p.provision_key for p in result.provisions]
    assert "99/2026/QH15#D2" in keys
    assert result.warnings == (UNBALANCED_QUOTES_WARNING,)


def test_document_without_articles_raises() -> None:
    with pytest.raises(LegalParseError):
        parse_legal_structure("Chỉ là một đoạn văn bản thông thường.", N)


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


def test_broken_quote_recovers_at_next_outer_article_without_damaging_earlier_quotes() -> None:
    number = "50/2026/QH15"
    result = parse_legal_structure(BROKEN_SECOND_QUOTE, number)
    provisions = {p.provision_key: p for p in result.provisions}
    assert list(provisions) == [
        f"{number}#D1",
        f"{number}#D1.K1",
        f"{number}#D1.K2",
        f"{number}#D2",
    ]
    assert "2. Định nghĩa B.”" in provisions[f"{number}#D1.K1"].text
    assert provisions[f"{number}#D1.K2"].text.startswith("2. Sửa đổi khoản 1 Điều 9")
    assert provisions[f"{number}#D2"].text.startswith("Điều 2. Hiệu lực thi hành")
    assert result.warnings == (UNBALANCED_QUOTES_WARNING,)


def test_duplicate_provision_key_is_kept_as_text_with_warning() -> None:
    result = parse_legal_structure("Điều 1. Tên\n1. Thứ nhất.\n1. Lặp lại.", N)
    provisions = {p.provision_key: p for p in result.provisions}
    assert provisions[f"{N}#D1.K1"].text == "1. Thứ nhất.\n1. Lặp lại."
    assert result.warnings == (DUPLICATE_PROVISION_KEY_WARNING,)
