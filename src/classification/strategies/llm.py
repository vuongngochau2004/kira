"""
LLM-based classification strategy.

Uses LLM to classify query intent when keyword/cached strategies fail.
"""

import asyncio
from typing import Any
from uuid import UUID

from src.protocols.classification import (
    ClassificationStrategy,
    ClassificationResult,
    Intent
)
from src.agents.llm import chat_async
from src.agents.utils import parse_json_response


# Routing classifier prompt
ROUTING_CLASSIFIER_PROMPT = """Bạn là classifier phân loại câu hỏi trong hệ thống K.I.R.A.

Phân tích câu hỏi và chọn loại intent phù hợp nhất:

**Câu hỏi:** {query}

**Các loại intent:**
1. **conversational** - Chào hỏi, cảm ơn, chat thông thường, hỏi về bot
   Ví dụ: "xin chào", "cảm ơn", "bạn tên gì", "bot làm được gì"

2. **rag** - Câu hỏi cần tìm kiếm trong tài liệu, kiến thức từ database
   Ví dụ: "điều khoản hợp đồng", "quy định về lao động", "thủ tục thành lập công ty"

**Yêu cầu:**
- Chọn MỘT loại phù hợp nhất
- Đánh giá độ tự tin (confidence: 0.0 đến 1.0)
- Giải thích ngắn gọn lý do

**Trả về JSON:**
```json
{{
    "intent": "conversational|rag",
    "confidence": 0.0-1.0,
    "reason": "lý do ngắn gọn"
}}
```"""


class LLMStrategy(ClassificationStrategy):
    """
    LLM-based classification strategy.

    Uses LLM to classify query intent. Fallback strategy when keyword/cached
    strategies cannot classify with high confidence.
    Target latency: ~800ms (p95).

    Attributes:
        temperature: LLM temperature for consistent classification
        max_tokens: Maximum tokens in LLM response
        timeout: Timeout for LLM calls in seconds

    Example:
        >>> strategy = LLMStrategy(temperature=0.1)
        >>> result = await strategy.classify("điều khoản hợp đồng", "user123")
        >>> assert result.intent == Intent.RAG
    """

    def __init__(
        self,
        temperature: float = 0.1,
        max_tokens: int = 100,
        timeout: int = 30
    ):
        """
        Initialize LLM strategy.

        Args:
            temperature: Low temperature for consistent classification
            max_tokens: Max tokens in LLM response
            timeout: Timeout for LLM calls in seconds
        """
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def can_handle(self, query: str, user_id: str | UUID) -> bool:
        """
        LLM strategy can handle any query.

        Args:
            query: User query string
            user_id: User ID

        Returns:
            Always True (LLM can classify anything)
        """
        return bool(query and query.strip())

    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        """
        Classify query using LLM.

        Args:
            query: User query string
            user_id: User ID (not used in LLM classification but required by protocol)
            context: Additional context (optional conversation history for context)

        Returns:
            ClassificationResult with intent and confidence

        Raises:
            TimeoutError: If LLM call exceeds timeout
        """
        if not query or not query.strip():
            return ClassificationResult(
                intent=Intent.CONVERSATIONAL,
                confidence=0.0,
                reason="Empty query"
            )

        try:
            # Run LLM call with timeout
            result = await asyncio.wait_for(
                self._classify_with_llm(query, context),
                timeout=self.timeout
            )

            return result

        except asyncio.TimeoutError:
            # Fallback on timeout
            return ClassificationResult(
                intent=Intent.RAG,  # Safer default
                confidence=0.3,
                reason=f"LLM timeout after {self.timeout}s, using default RAG",
                metadata={"strategy": "llm", "error": "timeout"}
            )

        except Exception as e:
            # Fallback on error
            return ClassificationResult(
                intent=Intent.RAG,  # Safer default
                confidence=0.3,
                reason=f"LLM classification error: {str(e)}",
                metadata={"strategy": "llm", "error": str(e)}
            )

    async def _classify_with_llm(
        self,
        query: str,
        context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        """
        Internal method to classify with LLM.

        Args:
            query: User query string
            context: Additional context

        Returns:
            ClassificationResult
        """
        # Format prompt
        prompt = ROUTING_CLASSIFIER_PROMPT.format(query=query)

        # Call LLM
        response = await chat_async(
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # Parse JSON response
        parsed = parse_json_response(response["content"])

        if not parsed:
            # Fallback if parsing fails
            return ClassificationResult(
                intent=Intent.RAG,
                confidence=0.5,
                reason="JSON parsing failed, using default RAG",
                metadata={"strategy": "llm", "parse_error": True}
            )

        # Map intent string to Intent enum
        intent_str = parsed.get("intent", "rag").lower()
        intent = self._map_intent(intent_str)

        confidence = float(parsed.get("confidence", 0.5))
        reason = parsed.get("reason", "")

        # Validate confidence range
        confidence = max(0.0, min(1.0, confidence))

        return ClassificationResult(
            intent=intent,
            confidence=confidence,
            reason=reason,
            metadata={"strategy": "llm"},
            handler_hint=self._get_handler_hint(intent)
        )

    def _map_intent(self, intent_str: str) -> Intent:
        """
        Map intent string to Intent enum.

        Args:
            intent_str: Intent string from LLM

        Returns:
            Intent enum value

        Example:
            >>> strategy = LLMStrategy()
            >>> strategy._map_intent("rag") == Intent.RAG
            True
        """
        intent_map = {
            "rag": Intent.RAG,
            "conversational": Intent.CONVERSATIONAL,
            "conversation": Intent.CONVERSATIONAL,
            "chat": Intent.CONVERSATIONAL,
        }

        return intent_map.get(intent_str.lower(), Intent.RAG)

    def _get_handler_hint(self, intent: Intent) -> str | None:
        """
        Get handler hint for intent.

        Args:
            intent: Intent enum

        Returns:
            Handler name or None

        Example:
            >>> strategy = LLMStrategy()
            >>> strategy._get_handler_hint(Intent.RAG)
            'RAGHandler'
        """
        handler_map = {
            Intent.RAG: "RAGHandler",
            Intent.CONVERSATIONAL: "ConversationalHandler",
        }

        return handler_map.get(intent)
