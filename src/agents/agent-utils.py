"""Utility functions for agents."""

import json
import re
from typing import Any

# =============================================================================
# CONSTANTS
# =============================================================================

# Conversational query detection keywords
CONVERSATIONAL_KEYWORDS = [
    # Greetings
    "hello", "hi", "hey", "chao", "xin chào", "bạn tên", "ten la gi",
    # Small talk
    "how are you", "bạn sao", "có khỏe không",
    # Gratitude
    "thanks", "cảm ơn", "thank you",
    # Farewell
    "goodbye", "tạm biệt", "bye",
    # Meta questions about the bot
    "bạn là ai", "you are", "bot làm được gì", "bạn làm gì",
    # Weather/time (common small talk)
    "nhiet độ", "weather", "thoi tiet",
]

# Maximum word count for very short conversational queries
MAX_SHORT_QUERY_WORDS = 2


def parse_json_response(content: str) -> dict[str, Any]:
    """Parse JSON from LLM response, handle markdown blocks.

    Args:
        content: Raw LLM response content

    Returns:
        Parsed JSON dict, or empty dict if parsing fails
    """
    content = content.strip()

    # Remove markdown code blocks
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON using regex
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}


def format_context(docs: list[Any]) -> str:
    """Format documents into context string.

    Args:
        docs: List of documents (dict or objects)

    Returns:
        Formatted context string
    """
    parts = []
    for i, doc in enumerate(docs):
        if isinstance(doc, dict):
            text = doc.get("text", doc.get("content", doc.get("page_content", "")))
        else:
            text = getattr(doc, "page_content", getattr(doc, "text", ""))
        parts.append(f"[{i+1}] {text}")
    return "\n\n".join(parts)


def is_conversational_query(query: str) -> bool:
    """Check if query is conversational (not research-related).

    Uses heuristic matching:
    1. Very short queries (≤2 words) are likely greetings
    2. Queries containing conversational keywords

    Note: This is a simple heuristic. For production, consider using
    semantic similarity or the QueryClassifier for better accuracy.

    Args:
        query: User query

    Returns:
        True if conversational, False if research query
    """
    query_lower = query.lower().strip()

    # Check for very short queries (likely greetings)
    if len(query_lower.split()) <= MAX_SHORT_QUERY_WORDS:
        return True

    # Check for conversational keywords
    return any(kw in query_lower for kw in CONVERSATIONAL_KEYWORDS)


__all__ = ["parse_json_response", "format_context", "is_conversational_query"]
