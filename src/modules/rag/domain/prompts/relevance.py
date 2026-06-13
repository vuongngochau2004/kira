"""Relevance evaluation prompts for the RAG domain."""


def build_relevance_evaluation_prompt(query: str, response: str, context: str) -> str:
    """Build prompt for structured RAG relevance evaluation."""
    return f"""Bạn đánh giá câu trả lời RAG có thực sự dựa trên tài liệu liên quan hay không.

CÂU HỎI:
{query}

NGỮ CẢNH/TÀI LIỆU ĐÃ TRUY XUẤT:
{context}

CÂU TRẢ LỜI:
{response}

Trả về DUY NHẤT JSON hợp lệ:
{{
  "has_relevant_docs": true hoặc false,
  "reason": "lý do ngắn gọn bằng tiếng Việt"
}}

Quy tắc:
- has_relevant_docs=false nếu tài liệu không liên quan, câu trả lời nói không có thông tin, hoặc không có căn cứ trực tiếp trong ngữ cảnh.
- has_relevant_docs=true nếu câu trả lời sử dụng căn cứ trực tiếp từ ngữ cảnh.
"""


__all__ = ["build_relevance_evaluation_prompt"]
