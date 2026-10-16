from datetime import date

import pytest

from src.modules.legal.domain.temporal import (
    TemporalQuery,
    default_temporal_query,
    resolve_temporal_rules,
)

TODAY = date(2026, 10, 15)


def _single(day: date, source: str = "rule") -> tuple[str, tuple[date, ...], str]:
    return ("single", (day,), source)


def _shape(result: TemporalQuery | None) -> tuple[str, tuple[date, ...], str] | None:
    return None if result is None else (result.mode, result.dates, result.source)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Mức phạt hiện nay là bao nhiêu?", _single(TODAY)),
        ("Thủ tục cấp sổ đỏ gồm những gì?", _single(TODAY, "default")),
        ("Quy định vào ngày 15/3/2025 thế nào?", _single(date(2025, 3, 15))),
        ("Trước ngày 1/7/2026 quy định thế nào?", _single(date(2026, 6, 30))),
        ("Từ ngày 1 tháng 7 năm 2026 áp dụng gì?", _single(date(2026, 7, 1))),
        ("Năm 2025 quy định ra sao?", _single(date(2025, 12, 31))),
        ("Trong năm 2026 thì sao?", _single(TODAY)),
        ("Trước năm 2025 thì sao?", _single(date(2024, 12, 31))),
        ("Từ năm 2027 có gì thay đổi về lệ phí?", _single(date(2027, 1, 1))),
        ("Luật Đất đai năm 2024 quy định gì về giá đất?", _single(TODAY, "default")),
        ("Luật Đất đai quy định thế nào vào năm 2023?", _single(date(2023, 12, 31))),
        ("Ngày 31/02/2026 có hiệu lực không?", _single(TODAY, "default")),
    ],
)
def test_single_date_resolution(question: str, expected: tuple) -> None:
    assert _shape(resolve_temporal_rules(question, TODAY)) == expected


def test_compare_around_one_date() -> None:
    result = resolve_temporal_rules("So sánh quy định trước và sau 1/7/2026", TODAY)
    assert _shape(result) == ("compare", (date(2026, 6, 30), date(2026, 7, 1)), "rule")


def test_compare_two_dates_sorted() -> None:
    result = resolve_temporal_rules("So sánh quy định ngày 1/7/2026 và ngày 1/1/2025", TODAY)
    assert _shape(result) == ("compare", (date(2025, 1, 1), date(2026, 7, 1)), "rule")


@pytest.mark.parametrize(
    "question",
    [
        "So sánh luật cũ và mới về thuế",
        "Trước khi Luật Đất đai 2024 có hiệu lực thì sao?",
        "Quy định ngày 1/1/2025 hay ngày 1/7/2026?",
    ],
)
def test_uncertain_questions_need_llm(question: str) -> None:
    assert resolve_temporal_rules(question, TODAY) is None


def test_default_query() -> None:
    assert default_temporal_query(TODAY) == TemporalQuery(
        mode="single", dates=(TODAY,), reason="no temporal reference", source="default"
    )


def test_compare_one_year_with_present() -> None:
    result = resolve_temporal_rules("So sánh quy định năm 2023 và hiện nay", TODAY)
    assert _shape(result) == ("compare", (date(2023, 12, 31), TODAY), "rule")


@pytest.mark.parametrize(
    "question",
    [
        "Luật Đất đai năm 2013 và năm 2024 khác gì?",
        "Điều 12 Luật Đất đai năm 2024 thay đổi gì so với năm 2013?",
    ],
)
def test_compare_with_one_bare_year_needs_llm(question: str) -> None:
    assert resolve_temporal_rules(question, TODAY) is None


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Theo Nghị định số 168 năm 2024 thì phạt bao nhiêu?", _single(TODAY, "default")),
        ("Mức phạt theo Nghị định 100 năm 2019 hiện nay?", _single(TODAY)),
    ],
)
def test_numbered_document_names_are_not_dates(question: str, expected: tuple) -> None:
    assert _shape(resolve_temporal_rules(question, TODAY)) == expected


def test_present_with_explicit_date_needs_llm() -> None:
    assert resolve_temporal_rules("Hiện nay so với ngày 1/1/2025 thì sao?", TODAY) is None
    assert resolve_temporal_rules("Hiện nay, năm 2019 quy định mức phạt nào?", TODAY) is None
