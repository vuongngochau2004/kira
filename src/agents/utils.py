"""Utility functions for agents."""

import json
import re
from typing import Any


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

    Args:
        query: User query

    Returns:
        True if conversational, False if research query
    """
    keywords = [
        "hello", "hi", "hey", "chao", "xin chào", "bạn tên",
        "ten la gi", "nhiet độ", "weather", "thoi tiet",
        "how are you", "bạn sao", "có khỏe không", "thanks", "cảm ơn",
        "goodbye", "tạm biệt", "bye"
    ]
    query_lower = query.lower().strip()
    # Very short queries (greetings)
    if len(query_lower.split()) <= 2:
        return True
    return any(kw in query_lower for kw in keywords)


__all__ = ["parse_json_response", "format_context", "is_conversational_query"]
