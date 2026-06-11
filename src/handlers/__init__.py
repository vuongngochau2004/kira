"""
Handlers package for query execution.

This package implements the QueryHandler protocol for different query types:
- RAGHandler: Document retrieval + LLM generation
- ConversationalHandler: Direct LLM chat without retrieval

Handlers receive pre-classified queries and execute domain-specific logic.
No classification logic should be in handlers (SRP compliance).
"""

from handlers.rag import RAGHandler
from handlers.conversational import ConversationalHandler

__all__ = [
    "RAGHandler",
    "ConversationalHandler",
]
