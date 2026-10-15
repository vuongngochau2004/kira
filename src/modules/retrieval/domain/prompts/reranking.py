"""LLM reranking and scoring prompts."""

RERANKING_SYSTEM_PROMPT = "Bạn là trợ lý chuyên gia phân tích và xếp hạng thông tin."
SCORING_SYSTEM_PROMPT = "Bạn là chuyên gia đánh giá độ liên quan của thông tin."


def build_reranking_prompt(query: str, formatted_documents: str) -> str:
    """Build prompt for relative document reranking."""
    return f"""Bạn là chuyên gia phân tích thông tin. Hãy xếp hạng các đoạn văn bản dưới đây theo độ liên quan đến câu hỏi.

CÂU HỎI: {query}

CÁC ĐOẠN VĂN BẢN:
{formatted_documents}

YÊU CẦU:
1. Đọc kỹ câu hỏi và từng đoạn văn bản
2. Xếp hạng các đoạn văn bản từ độ liên quan cao nhất đến thấp nhất
3. Chỉ trả về một mảng JSON chứa số thứ tự của các đoạn văn bản đã được xếp hạng

Định dạng trả về: [số_thứ_tự_0, số_thứ_tự_1, ...]
Ví dụ: [3, 0, 4, 1, 2]

Trả về chỉ mảng JSON, không giải thích:"""


def build_scoring_prompt(query: str, document: str) -> str:
    """Build prompt for independent document relevance scoring."""
    return f"""Đánh giá độ liên quan của đoạn văn bản dưới đây đến câu hỏi.

CÂU HỎI: {query}

ĐOẠN VĂN BẢN:
{document}

Hãy đánh giá trên thang điểm từ 0.0 đến 1.0:
- 0.9-1.0: Rất liên quan, trực tiếp trả lời câu hỏi
- 0.7-0.9: Liên quan, chứa thông tin hữu ích
- 0.5-0.7: Có liên quan một phần
- 0.3-0.5: Liên quan ít
- 0.0-0.3: Không liên quan

Chỉ trả về một con số (float), không giải thích:"""


__all__ = [
    "RERANKING_SYSTEM_PROMPT",
    "SCORING_SYSTEM_PROMPT",
    "build_reranking_prompt",
    "build_scoring_prompt",
]
