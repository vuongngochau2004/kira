"""
Conversational domain service.

Business logic for conversational (non-RAG) query handling:
- Message formatting for LLM
- Conversation history management
- Response formatting

This service handles the domain rules for direct LLM chat
without document retrieval.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationContext:
    """Context for a conversational query.

    Attributes:
        query: User's message text
        conversation_history: Previous messages in the conversation
        system_prompt: System prompt for the LLM
        user_prompt_template: Template for formatting the user message
    """

    query: str
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    system_prompt: str = ""
    user_prompt_template: str = "{query}"


@dataclass
class ConversationResult:
    """Result of a conversational query.

    Attributes:
        content: LLM-generated response text
        metadata: Processing metadata (latency, handler name, etc.)
        thinking_content: Reasoning/thinking content if available
    """

    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    thinking_content: list[str] = field(default_factory=list)


class ConversationService:
    """Domain service for conversational query processing rules.

    Handles business logic for direct LLM chat:
    - Building message sequences for LLM calls
    - Validating conversation context
    - Formatting prompts with history
    """

    @staticmethod
    def build_messages(context: ConversationContext) -> list[dict[str, str]]:
        """Build LLM message sequence from conversation context.

        Constructs the message list in the format expected by LLM providers:
        system → history → user query.

        Args:
            context: Conversation context with query, history, and prompts

        Returns:
            List of message dicts with role and content keys

        Example:
            >>> ctx = ConversationContext(
            ...     query="Hello",
            ...     system_prompt="You are a helpful assistant.",
            ...     conversation_history=[{"role": "user", "content": "Hi"}],
            ... )
            >>> msgs = ConversationService.build_messages(ctx)
            >>> len(msgs)
            3
        """
        messages: list[dict[str, str]] = []

        # Add system prompt if provided
        if context.system_prompt:
            messages.append({"role": "system", "content": context.system_prompt})

        # Add conversation history
        if context.conversation_history:
            messages.extend(context.conversation_history)

        # Add current user message
        user_content = context.user_prompt_template.format(query=context.query)
        messages.append({"role": "user", "content": user_content})

        return messages

    @staticmethod
    def validate_context(context: ConversationContext) -> list[str]:
        """Validate conversation context for processing.

        Args:
            context: Conversation context to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        if not context.query or not context.query.strip():
            errors.append("Query cannot be empty")

        if len(context.query) > 5000:
            errors.append("Query exceeds maximum length (5000 chars)")

        return errors


__all__ = ["ConversationService", "ConversationContext", "ConversationResult"]