from src.modules.document.domain.services.cleaner import clean_document
from src.modules.document.domain.services.chunker import chunk_document


def test_clean_document_preserves_page_markers_when_stripping_html() -> None:
    text = "<!-- page 2 -->\n<p>Điều 1. Nội dung</p>"

    cleaned = clean_document(text)

    assert "<!-- page 2 -->" in cleaned
    assert "<p>" not in cleaned
    assert "Điều 1. Nội dung" in cleaned


def test_legal_chunking_uses_paragraph_boundaries_for_large_sections() -> None:
    text = "\n\n".join(
        [
            "<!-- page 1 -->",
            "Điều 1. Quy định kiểm thử",
            "Đoạn mở đầu của điều khoản với nội dung đủ dài để được tính như một khối riêng.",
            "- Khiển trách: áp dụng đối với thí sinh vi phạm một lần trong phòng thi.",
            "- Cảnh cáo: áp dụng đối với thí sinh tiếp tục vi phạm trong thời gian thi.",
            "<!-- page 2 -->",
            "- Đình chỉ thi: áp dụng đối với thí sinh mang tài liệu vào phòng thi.",
            "- Buộc thôi học: áp dụng đối với hành vi vi phạm nghiêm trọng theo quy định.",
        ]
    )

    chunks = chunk_document(
        text,
        document_id="doc-1",
        chunk_size=45,
        chunk_overlap=10,
    )

    assert len(chunks) > 1
    assert all(chunk.metadata["chunking_strategy"] == "legal_structure" for chunk in chunks)
    assert chunks[0].metadata.get("page_start") == 1
    assert any(chunk.metadata.get("page_start") == 1 for chunk in chunks)
    assert any(chunk.metadata.get("page_start") == 2 for chunk in chunks)
    assert all(
        chunk.content.startswith(("<!-- page", "Điều", "Đoạn", "- "))
        for chunk in chunks
    )
