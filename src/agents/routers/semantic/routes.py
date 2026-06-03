"""Semantic route definitions for KIRA query routing."""

from semantic_router import Route

# Conversational route utterances (20+ examples)
CONVERSATIONAL_UTTERANCES = [
    # Greetings
    "xin chào",
    "hello",
    "hi there",
    "chào bạn",
    "chào buổi sáng",
    "chào buổi tối",
    "good morning",
    "good evening",
    "hey",

    # About the bot
    "bạn tên gì",
    "bạn là ai",
    "kira là gì",
    "bot làm được gì",
    "you can do what",
    "tell me about yourself",
    "what can you do",
    " giới thiệu bản thân",

    # Gratitude
    "cảm ơn",
    "thanks",
    "thank you",
    "thank you very much",
    "cám ơn",

    # Farewell
    "tạm biệt",
    "goodbye",
    "bye",
    "see you",
    "hẹn gặp lại",

    # Small talk
    "bạn khỏe không",
    "how are you",
    "như thế nào",
    "weather today",
    "thời tiết hôm nay",
    "bạn thế nào",

    # Help/instruction
    "tôi nên bắt đầu thế nào",
    "how to use",
    "hướng dẫn sử dụng",
    "help",
    "giúp đỡ",
]

# RAG Legal route utterances (30+ examples)
RAG_LEGAL_UTTERANCES = [
    # Contract queries
    "điều khoản hợp đồng",
    "contract terms",
    "hợp đồng",
    "khoản trong hợp đồng",
    "clause in contract",
    "cam kết trong agreement",
    "nội dung hợp đồng",

    # Law/regulation queries
    "quy định về lao động",
    "labor law regulations",
    "luật lao động",
    "bộ luật dân sự",
    "civil code",
    "civil law",
    "nghị định",
    "decree",
    "thông tư",
    "circular",

    # Procedure queries
    "thủ tục thành lập công ty",
    "company formation procedure",
    "cách đăng ký doanh nghiệp",
    "business registration",

    # Specific legal terms
    "điều kiện tuyển dụng",
    "hiring requirements",
    "quy trình tuyển dụng",
    "chế độ thưởng",
    "bonus policy",
    "lương thưởng",
    "thời gian làm việc",
    "working hours",
    "giờ làm việc",

    # Short queries (critical - these were misrouted)
    "hợp đồng",
    "luật",
    "nghị định",
    "quy định",
    "thông tư",
    "contract",
    "law",
    "regulation",
    "terms",

    # Query patterns
    "tìm về",
    "search for",
    "tra cứu",
    "lookup",
    "trong tài liệu",
    "in documents",
    "văn bản pháp lý",

    # More legal domain specific
    "pháp luật",
    "legal",
    "quy chế",
    "chính sách",
    "policy",
    "điều ước",
    "hiến pháp",
    "luật thương mại",
]


def get_conversational_route() -> Route:
    """Get conversational route definition."""
    return Route(
        name="conversational",
        utterances=CONVERSATIONAL_UTTERANCES,
    )


def get_rag_legal_route() -> Route:
    """Get RAG legal route definition."""
    return Route(
        name="rag_legal",
        utterances=RAG_LEGAL_UTTERANCES,
    )


def get_all_routes() -> list[Route]:
    """Get all defined routes."""
    return [
        get_conversational_route(),
        get_rag_legal_route(),
    ]


__all__ = [
    "CONVERSATIONAL_UTTERANCES",
    "RAG_LEGAL_UTTERANCES",
    "get_conversational_route",
    "get_rag_legal_route",
    "get_all_routes",
]
