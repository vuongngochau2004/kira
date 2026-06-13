"""DOCX rendering for generated administrative documents."""

from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt


def render_administrative_docx(content: str) -> bytes:
    """Render a drafted administrative document into DOCX bytes."""
    document = Document()

    normal_style = document.styles["Normal"]
    normal_style.font.name = "Times New Roman"
    normal_style.font.size = Pt(13)

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            document.add_paragraph()
            continue

        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(6)

        if _looks_like_national_header(line):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(line)
            run.bold = True
        elif _looks_like_title(line):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(line)
            run.bold = True
            run.font.size = Pt(14)
        elif _looks_like_signature_block(line):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(line)
            run.bold = True
        else:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            paragraph.add_run(line)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _looks_like_national_header(line: str) -> bool:
    upper = line.upper()
    return "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in upper or "ĐỘC LẬP" in upper


def _looks_like_title(line: str) -> bool:
    upper = line.upper()
    title_markers = ("CÔNG VĂN", "TỜ TRÌNH", "QUYẾT ĐỊNH", "THÔNG BÁO", "KẾ HOẠCH", "BIÊN BẢN")
    return any(marker in upper for marker in title_markers)


def _looks_like_signature_block(line: str) -> bool:
    upper = line.upper()
    return upper.startswith(("THỦ TRƯỞNG", "HIỆU TRƯỞNG", "GIÁM ĐỐC", "TRƯỞNG PHÒNG", "NGƯỜI KÝ"))


__all__ = ["render_administrative_docx"]
