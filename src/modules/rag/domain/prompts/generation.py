"""Generation prompts for the RAG domain."""


def build_generation_prompt(query: str, context: str) -> str:
    """Build prompt for answer generation from retrieved context."""
    return f"""Bạn là trợ lý hữu ích, chỉ trả lời câu hỏi dựa trên ngữ cảnh được cung cấp.

NGỮ CẢNH:
{context}

CÂU HỎI: {query}

HƯỚNG DẪN:
1. Chỉ sử dụng thông tin trong ngữ cảnh ở trên để trả lời.
2. Nếu ngữ cảnh không chứa thông tin liên quan đến câu hỏi, hãy nói rõ.
3. Trình bày câu trả lời rõ ràng, có cấu trúc tốt.
4. Nếu thông tin mâu thuẫn, hãy nêu rõ điểm khác biệt.
5. Trả lời bằng tiếng Việt.
6. Ngắn gọn nhưng đầy đủ.
7. KHÔNG trích dẫn cứng nhắc số Điều/Khoản (ví dụ: "Điều 11", "Điều 12") trừ khi người dùng yêu cầu rõ. Hãy tổng hợp và giải thích quy định một cách tự nhiên.

TRẢ LỜI:"""


def build_regeneration_prompt(
    query: str,
    context: str,
    previous_response: str,
    feedback: str,
) -> str:
    """Build prompt for answer regeneration from quality feedback."""
    return f"""Bạn đang cải thiện câu trả lời trước đó dựa trên phản hồi chất lượng.

NGỮ CẢNH:
{context}

CÂU HỎI: {query}

CÂU TRẢ LỜI TRƯỚC:
{previous_response}

PHẢN HỒI CẦN CẢI THIỆN:
{feedback}

HƯỚNG DẪN:
1. Xử lý đúng các vấn đề cụ thể được nêu trong phản hồi.
2. Cải thiện chất lượng câu trả lời.
3. Cung cấp câu trả lời đầy đủ và chính xác hơn.
4. Sử dụng tiếng Việt.

CÂU TRẢ LỜI ĐÃ CẢI THIỆN:"""


__all__ = ["build_generation_prompt", "build_regeneration_prompt"]
