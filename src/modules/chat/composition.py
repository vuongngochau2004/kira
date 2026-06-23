"""Dependency composition for the chat module."""

from src.modules.chat.application.chat import ChatUseCase
from src.modules.chat.application.citations import EnrichCitations
from src.modules.chat.infrastructure.handlers.conversational import ConversationalHandler
from src.modules.chat.infrastructure.handlers.drafting_handler import AdministrativeDraftingHandler
from src.modules.chat.infrastructure.handlers.rag_handler import RAGHandler
from src.modules.chat.infrastructure.persistence.conversation_repository import (
    create_conversation,
    create_message,
    get_conversation,
    get_conversation_messages,
    list_conversations,
)
from src.shared.ports.classification import Intent
from src.modules.retrieval.infrastructure.retrieval_adapters import PostgresRetrievalDocumentAdapter


_chat_use_case: ChatUseCase | None = None


async def get_chat_use_case() -> ChatUseCase:
    """Get or create ChatUseCase with classifier and handlers from DI container."""
    global _chat_use_case
    if _chat_use_case is None:
        from src.shared.kernel.di import get_container
        from src.shared.ports.classification import ClassificationStrategyBase

        container = await get_container()
        classifier = await container.get(ClassificationStrategyBase)

        conversational_handler = await container.get(ConversationalHandler)
        rag_handler = await container.get(RAGHandler)
        drafting_handler = await container.get(AdministrativeDraftingHandler)

        _chat_use_case = ChatUseCase(
            classifier=classifier,
            handlers={
                Intent.CONVERSATIONAL: conversational_handler,
                Intent.RAG: rag_handler,
                Intent.DRAFTING: drafting_handler,
            },
        )
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
    "list_conversations",
]
