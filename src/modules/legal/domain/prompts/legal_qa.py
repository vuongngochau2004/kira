"""Prompt and citation formatting for point-in-time legal answers."""

from collections.abc import Sequence
from datetime import date
from typing import Any

from src.modules.legal.domain.qa import LegalSource
from src.modules.legal.domain.temporal import TemporalQuery

GRAPH_UNAVAILABLE_NOTICE = (
    "Chưa kiểm tra được các văn bản liên quan (hướng dẫn, sửa đổi) do hệ thống đồ thị pháp luật "
    "tạm thời không khả dụng."
)

_ROLE_NOTES = {
    "guide": "(Văn bản hướng dẫn thi hành)",
    "before": "(Quy định trước thay đổi)",
    "after": "(Quy định sau thay đổi)",
    "removed": "(Không còn hiệu lực ở thời điểm sau)",
    "added": "(Quy định mới, chưa có ở thời điểm trước)",
}

LEGAL_QA_SYSTEM_PROMPT = """Bạn là trợ lý pháp luật Việt Nam của hệ thống KIRA.

QUY TẮC BẮT BUỘC:
1. Chỉ trả lời dựa trên các NGUỒN được cung cấp; không dùng kiến thức bên ngoài.
2. Mỗi nhận định phải kèm trích dẫn [n] tương ứng với nguồn, và nêu rõ Điều/Khoản cùng số hiệu văn bản.
3. Câu đầu tiên của câu trả lời phải lặp lại nguyên văn dòng NGÀY ÁP DỤNG.
4. Nếu một nguồn ghi "đã được sửa đổi từ ngày ...", phải nói rõ quy định đã thay đổi sau thời điểm hỏi.
5. Khi so sánh hai thời điểm, trình bày quy định trước và sau thay đổi, nêu văn bản đã gây ra thay đổi.
6. Văn bản hướng dẫn thi hành chỉ dùng để làm rõ, không thay thế quy định của luật.
7. Nếu các nguồn không đủ để trả lời, nói rõ là không tìm thấy quy định phù hợp; không suy đoán.
8. Trả lời bằng tiếng Việt, ngắn gọn, có cấu trúc."""


def format_day(day: date) -> str:
    return day.strftime("%d/%m/%Y")


def validity_text(valid_from: date, valid_to: date | None) -> str:
    end = format_day(valid_to) if valid_to else "nay"
    return f"hiệu lực {format_day(valid_from)} → {end}"


def applied_date_sentence(temporal: TemporalQuery) -> str:
    if temporal.mode == "compare":
        first, second = temporal.dates
        return f"So sánh quy định tại ngày {format_day(first)} và ngày {format_day(second)}."
    return f"Áp dụng tại ngày {format_day(temporal.dates[0])}."


def not_found_message(temporal: TemporalQuery) -> str:
    return (
        f"{applied_date_sentence(temporal)} Không tìm thấy quy định pháp luật có hiệu lực phù hợp "
        "với câu hỏi trong kho văn bản hiện có."
    )


def source_block(index: int, source: LegalSource) -> str:
    hit = source.hit
    lines = [
        f"[{index}] {hit.label} — {hit.title} số {hit.number} — "
        f"{validity_text(hit.valid_from, hit.valid_to)}"
    ]
    if source.role in _ROLE_NOTES:
        lines.append(_ROLE_NOTES[source.role])
    if source.parent_label and source.parent_text:
        lines.append(f"Thuộc {source.parent_label}: {source.parent_text[:400]}")
    if source.introduced_by_number:
        title = source.introduced_by_title or "văn bản"
        lines.append(f"Nội dung này được sửa đổi bởi {title} số {source.introduced_by_number}.")
    if source.amended_after:
        lines.append(
            f"Lưu ý: quy định này đã được sửa đổi từ ngày {format_day(source.amended_after)}."
        )
    lines.append(hit.text)
    return "\n".join(lines)


def build_legal_qa_messages(
    question: str,
    temporal: TemporalQuery,
    sources: Sequence[LegalSource],
    notices: Sequence[str],
) -> list[dict[str, str]]:
    blocks = "\n\n".join(source_block(i, source) for i, source in enumerate(sources, start=1))
    parts = [f"NGÀY ÁP DỤNG: {applied_date_sentence(temporal)}", f"NGUỒN:\n\n{blocks}"]
    if notices:
        parts.append("GHI CHÚ:\n" + "\n".join(f"- {notice}" for notice in notices))
    parts.append(f"CÂU HỎI: {question}")
    return [
        {"role": "system", "content": LEGAL_QA_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


def citation_payload(source: LegalSource, snippet_length: int) -> dict[str, Any]:
    """Citation dict for the chat SSE metadata event (no document_id on purpose)."""
    hit = source.hit
    return {
        "filename": f"{hit.label} — {hit.title} ({hit.number})",
        "text": hit.text[:snippet_length],
        "page": hit.page,
        "confidence": hit.score,
        "chunk_id": hit.version_id,
        "legal": {
            "number": hit.number,
            "doc_type": hit.doc_type,
            "provision_key": hit.provision_key,
            "label": hit.label,
            "title": hit.title,
            "valid_from": hit.valid_from.isoformat(),
            "valid_to": hit.valid_to.isoformat() if hit.valid_to else None,
            "amended_after": source.amended_after.isoformat() if source.amended_after else None,
            "role": source.role,
        },
    }
