"""Dependency composition for the chat module."""

from kira.chat.citations import EnrichCitations
from kira.chat.handlers.conversational import ConversationalHandler
from kira.chat.handlers.drafting import AdministrativeDraftingHandler
from kira.chat.handlers.rag import RAGHandler
from kira.chat.intent.base import Intent
from kira.chat.repository import (
    create_conversation,
    create_message,
    get_conversation,
    get_conversation_messages,
    get_recent_owned_messages,
    list_conversations,
)
from kira.chat.service import ChatUseCase
from kira.config import settings
from kira.retrieval.adapters import PostgresRetrievalDocumentAdapter

_chat_use_case: ChatUseCase | None = None


async def get_chat_use_case() -> ChatUseCase:
    """Get or create ChatUseCase with classifier and handlers from DI container."""
    global _chat_use_case
    if _chat_use_case is None:
        from kira.chat.intent.base import ClassificationStrategyBase
        from kira.di.registry import get_container

        container = await get_container()
        classifier = await container.get(ClassificationStrategyBase)

        conversational_handler = await container.get(ConversationalHandler)
        rag_handler = await container.get(RAGHandler)
        drafting_handler = await container.get(AdministrativeDraftingHandler)

        handlers = {
            Intent.CONVERSATIONAL: conversational_handler,
            Intent.RAG: rag_handler,
            Intent.DRAFTING: drafting_handler,
        }
        if settings.legal_enabled:
            from kira.legal.chat_handler import LegalQAHandler

            handlers[Intent.LEGAL_QA] = await container.get(LegalQAHandler)
        _chat_use_case = ChatUseCase(classifier=classifier, handlers=handlers)
    return _chat_use_case


def citation_enricher() -> EnrichCitations:
    """Compose the citation enrichment application service."""
    return EnrichCitations(documents=PostgresRetrievalDocumentAdapter())


__all__ = [
    "create_conversation",
    "create_message",
    "citation_enricher",
    "get_chat_use_case",
    "get_conversation",
    "get_conversation_messages",
    "get_recent_owned_messages",
    "list_conversations",
]
