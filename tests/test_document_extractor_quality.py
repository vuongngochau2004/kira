from src.modules.document.domain.services.extractor import (
    _analyze_vietnamese_text_quality,
    _should_fallback_to_ocr,
    _vietnamese_text_quality_issues,
)


def test_vietnamese_quality_gate_flags_corrupted_text_layer() -> None:
    text = (
        "CONG HOA xA 1191 CHU NGHTA VIT NAM\n"
        "Dc 1p - Tir do - Hinh phñc\n"
        "QUYET DNH\n"
        "V vic ban hãnh Quy d!nh m&i thinh giãng và quãn 1 cong tác thinh giáng\n"
        "Can cu Luat Giao duc dai hoc va cac quy dinh ve dao tao cua nha truong\n"
        "Truong Dai hoc Bach khoa ban hanh quy dinh ve cong tac quan ly dao tao\n"
        "Cac don vi, to chuc va ca nhan co lien quan chiu trach nhiem thi hanh"
    )

    issues = _vietnamese_text_quality_issues(text, lang="vi")
    report = _analyze_vietnamese_text_quality(text, lang="vi")

    assert "many_unaccented_vietnamese_terms" in issues
    assert "mojibake_or_placeholder_chars" in issues
    assert report.score >= 3
    assert report.should_fallback
    assert _should_fallback_to_ocr(issues)


def test_vietnamese_quality_gate_accepts_clean_ocr_text() -> None:
    text = (
        "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
        "Độc lập - Tự do - Hạnh phúc\n"
        "QUYẾT ĐỊNH\n"
        "Về việc ban hành Quy định mời thỉnh giảng và quản lý công tác thỉnh giảng"
    )

    assert _vietnamese_text_quality_issues(text, lang="vi") == []
    assert _analyze_vietnamese_text_quality(text, lang="vi").score == 0


def test_vietnamese_quality_gate_does_not_fallback_on_single_minor_issue() -> None:
    issues = ["html_entities_in_text"]

    assert not _should_fallback_to_ocr(issues)
