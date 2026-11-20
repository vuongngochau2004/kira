"""Bound saved conversation context and resolve document follow-up searches."""

import re
from typing import TypedDict


class ConversationTurn(TypedDict):
    """One saved, user-owned conversational turn."""

    role: str
    content: str


_FOLLOW_UP = re.compile(
    r"\b(?:its|it|this|that|those|these|their|them|previous|above)\b"
    r"|(?:\bnó\b|\bđó\b|\bnày\b|\bấy\b|\btrên\b|\bcòn\b|\bthế còn\b)",
    re.IGNORECASE,
)
_EXPLICIT_FILE = re.compile(
    r"\b[\w-]+\.(?:pdf|docx?|txt)\b|\b(?:file|pdf|document)\b"
    r"|(?:tài liệu|tệp|tải lên|đã tải|của tôi)",
    re.IGNORECASE,
)


def bound_history(
    history: list[ConversationTurn] | list[dict[str, str]] | None,
    *,
    max_turns: int = 8,
    max_chars: int = 4000,
) -> list[ConversationTurn]:
    """Keep recent saved user/assistant text within an explicit request budget."""
    if not history or max_turns <= 0 or max_chars <= 0:
        return []

    result: list[ConversationTurn] = []
    remaining = max_chars
    per_turn = max(1, max_chars // max_turns)
    for raw in reversed(history):
        if len(result) >= max_turns or remaining <= 0:
            break
        role = raw.get("role")
        content = raw.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue
        clipped = content[: min(remaining, per_turn)]
        result.append({"role": role, "content": clipped})
        remaining -= len(clipped)
    return list(reversed(result))


def is_follow_up(query: str) -> bool:
    """Detect explicit references to earlier conversation turns."""
    return bool(_FOLLOW_UP.search(query))


def is_standalone_topic(query: str) -> bool:
    """Treat explicit file references as usable anchors even with a pronoun."""
    return not is_follow_up(query) or bool(_EXPLICIT_FILE.search(query))


def resolve_retrieval_query(query: str, history: list[ConversationTurn]) -> str:
    """Attach the most recent standalone user topic to an anaphoric search."""
    if not is_follow_up(query):
        return query
    for turn in reversed(history):
        if turn["role"] == "user" and is_standalone_topic(turn["content"]):
            return f"{turn['content'][:1000]} {query}"[:2000]
    return query
