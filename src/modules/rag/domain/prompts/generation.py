"""Generation prompts for the RAG domain."""


def build_generation_prompt(query: str, context: str) -> str:
    """Build prompt for answer generation from retrieved context."""
    return f"""Bạn là trợ lý hữu ích, chỉ trả lời câu hỏi dựa trên ngữ cảnh được cung cấp.

NGỮ CẢNH:
{context}

CÂU HỎI: {query}

HƯỚNG DẪN:
1. Câu đầu tiên phải trả lời trực tiếp vào câu hỏi, không mở đầu bằng lời dẫn chung.
2. Chỉ sử dụng thông tin trong ngữ cảnh ở trên để trả lời.
3. Nếu ngữ cảnh không chứa thông tin liên quan đến câu hỏi, hãy nói rõ ngay ở câu đầu.
4. Với câu hỏi về điều kiện, trách nhiệm, thủ tục hoặc quy trình: nêu kết luận trực tiếp trước, sau đó liệt kê các điều kiện/bước/chủ thể liên quan.
5. Trình bày câu trả lời rõ ràng, có cấu trúc tốt.
6. Nếu thông tin mâu thuẫn, hãy nêu rõ điểm khác biệt.
7. Trả lời bằng tiếng Việt.
8. Ngắn gọn nhưng đầy đủ.
9. KHÔNG trích dẫn cứng nhắc số Điều/Khoản (ví dụ: "Điều 11", "Điều 12") trừ khi người dùng yêu cầu rõ. Hãy tổng hợp và giải thích quy định một cách tự nhiên.

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
1. Câu đầu tiên phải trả lời trực tiếp vào câu hỏi.
2. Xử lý đúng các vấn đề cụ thể được nêu trong phản hồi.
3. Cải thiện chất lượng câu trả lời.
4. Cung cấp câu trả lời đầy đủ và chính xác hơn.
5. Sử dụng tiếng Việt.

CÂU TRẢ LỜI ĐÃ CẢI THIỆN:"""


__all__ = ["build_generation_prompt", "build_regeneration_prompt"]
