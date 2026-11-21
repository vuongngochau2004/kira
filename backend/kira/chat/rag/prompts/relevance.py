"""Relevance evaluation prompts for the RAG domain."""


def build_relevance_evaluation_prompt(query: str, response: str, context: str) -> str:
    """Build prompt for structured RAG relevance evaluation."""
    return f"""Bạn là một chuyên gia đánh giá độc lập. Hãy đánh giá xem tài liệu/ngữ cảnh đã truy xuất có thực sự chứa thông tin liên quan đến câu hỏi hay không, và câu trả lời có dựa trên tài liệu liên quan đó hay không.

CÂU HỎI CỦA NGƯỜI DÙNG:
{query}

NGỮ CẢNH/TÀI LIỆU ĐÃ TRUY XUẤT:
{context}

CÂU TRẢ LỜI ĐƯỢC ĐƯA RA:
{response}

Trả về DUY NHẤT một JSON hợp lệ:
{{
  "has_relevant_docs": true/false,
  "reason": "lý do ngắn gọn bằng tiếng Việt giải thích tại sao liên quan hoặc không liên quan"
}}

Quy tắc đánh giá:
1. has_relevant_docs = false nếu:
   - Ngữ cảnh/tài liệu được truy xuất KHÔNG liên quan đến chủ đề của câu hỏi người dùng.
   - Câu trả lời nói rằng không tìm thấy thông tin hoặc tài liệu không đề cập đến câu hỏi.
   - Tài liệu truy xuất là vô nghĩa hoặc không có căn cứ trực tiếp cho câu hỏi.
2. has_relevant_docs = true nếu:
   - Ngữ cảnh/tài liệu thực sự chứa câu trả lời trực tiếp cho câu hỏi của người dùng, và câu trả lời đã sử dụng thông tin chính xác từ đó.
3. Đánh giá dựa trên sự trùng khớp về nội dung và chủ đề ngữ nghĩa cốt lõi của câu hỏi và ngữ cảnh.
"""


__all__ = ["build_relevance_evaluation_prompt"]
