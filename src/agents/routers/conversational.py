"""Conversational router for casual chat and greetings."""

import time
import logging
from uuid import UUID
from typing import Any, AsyncIterator

from src.agents.llm import chat_async, chat_async_stream
from src.agents.prompts import CONVERSATIONAL_PROMPT
from src.agents.utils import is_conversational_query
from src.agents.routers.base import BaseRouter

logger = logging.getLogger(__name__)


class ConversationalRouter(BaseRouter):
    """Router for conversational queries (greetings, thanks, casual chat)."""

    # Keywords for conversational queries
    CONVERSATIONAL_KEYWORDS = [
        "hello", "hi", "hey", "chao", "xin chào",
        "bạn tên", "ten la gi", "tên là gì",
        "nhiet độ", "weather", "thoi tiet",
        "how are you", "bạn sao", "có khỏe không",
        "thanks", "cảm ơn", "thank",
        "goodbye", "tạm biệt", "bye",
        "chào buổi sáng", "chào buổi tối",
        "bot", "ai", "trợ lý"
    ]

    def __init__(self, max_retries: int = 2):
        """Initialize conversational router.

        Args:
            max_retries: Max retry attempts for LLM calls
        """
        self.max_retries = max_retries

    async def can_handle(self, query: str) -> float:
        """Check if query is conversational with confidence scoring.

        Args:
            query: User query

        Returns:
            Confidence score 0.0-1.0
        """
        query_lower = query.lower().strip()

        # Very short queries (likely greetings) - high confidence
        if len(query_lower.split()) <= 2:
            return 0.9

        # Check for conversational keywords
        keyword_matches = sum(
            1 for kw in self.CONVERSATIONAL_KEYWORDS
            if kw in query_lower
        )

        if keyword_matches >= 2:
            return 0.95  # Multiple keywords - very confident
        if keyword_matches == 1:
            return 0.85  # One keyword match

        # Fallback to original utility function
        if is_conversational_query(query):
            return 0.75

        return 0.0

    async def handle(self, query: str, user_id: str | UUID) -> dict[str, Any]:
        """Generate conversational response.

        Args:
            query: User query
            user_id: User ID (not used for conversational)

        Returns:
            Response dict with conversational answer
        """
        t0 = time.perf_counter()

        system_content = (
            "Bạn là K.I.R.A (Knowledge & Intelligent Robotic Assistant), một trợ lý AI thân thiện.\n\n"
            "Trước khi trả lời, hãy viết ra quá trình suy luận ngắn gọn của bạn và đặt trong thẻ <thinking>...</thinking>. "
            "Sau đó đưa ra câu trả lời chính thức bên ngoài thẻ.\n\n"
            "Ví dụ:\n"
            "<thinking>\n"
            "Người dùng chào hỏi. Cần phản hồi thân thiện và đề xuất giúp đỡ.\n"
            "</thinking>\n"
            "[Câu trả lời chính thức ở đây]"
        )
        user_content = f"Câu hỏi: {query}\n\nTrả lời ngắn gọn, thân thiện bằng tiếng Việt (1-2 câu)."

        for attempt in range(self.max_retries + 1):
            try:
                response = await chat_async(
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.8,
                    max_tokens=400,
                )

                return {
                    "content": response["content"],
                    "status": "conversational",
                    "citations": [],
                    "sources": [],
                    "metadata": {
                        "router": self.get_name(),
                        "agent": "conversational",
                    },
                    "latency_ms": (time.perf_counter() - t0) * 1000,
                    "retrieval_history": [],
                }
            except Exception as e:
                if attempt == self.max_retries:
                    return {
                        "content": "Xin lỗi, tôi không thể trả lời ngay lúc này.",
                        "status": "error",
                        "error": str(e),
                        "citations": [],
                        "sources": [],
                        "metadata": {"router": self.get_name(), "agent": "conversational"},
                        "latency_ms": (time.perf_counter() - t0) * 1000,
                        "retrieval_history": [],
                    }

    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
    ) -> AsyncIterator[dict]:
        """Generate conversational response stream."""
        t0 = time.perf_counter()

        system_content = (
            "Bạn là K.I.R.A (Knowledge & Intelligent Robotic Assistant), một trợ lý AI thân thiện.\n\n"
            "Trước khi trả lời, hãy viết ra quá trình suy luận ngắn gọn của bạn và đặt trong thẻ <thinking>...</thinking>. "
            "Sau đó đưa ra câu trả lời chính thức bên ngoài thẻ.\n\n"
            "Ví dụ:\n"
            "<thinking>\n"
            "Người dùng chào hỏi. Cần phản hồi thân thiện và đề xuất giúp đỡ.\n"
            "</thinking>\n"
            "[Câu trả lời chính thức ở đây]"
        )
        user_content = f"Câu hỏi: {query}\n\nTrả lời ngắn gọn, thân thiện bằng tiếng Việt (1-2 câu)."

        try:
            async for chunk in chat_async_stream(
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.8,
                max_tokens=400,
            ):
                yield {"type": "content", "data": {"text": chunk}}

            yield {
                "type": "metadata",
                "data": {
                    "status": "conversational",
                    "router": self.get_name(),
                    "agent": "conversational",
                    "latency_ms": (time.perf_counter() - t0) * 1000,
                },
            }
        except Exception as e:
            logger.error(f"ConversationalRouter stream error: {e}")
            yield {
                "type": "content",
                "data": {"text": "Xin lỗi, tôi không thể trả lời ngay lúc này."},
            }
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": str(e),
                    "router": self.get_name(),
                    "agent": "conversational",
                },
            }


__all__ = ["ConversationalRouter"]
