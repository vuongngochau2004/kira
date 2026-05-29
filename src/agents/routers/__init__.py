"""Routers package for multi-stage query routing.

Current implementation supports 2 intents:
- conversational: Chat, greetings, thanks
- rag: Document-based queries

Future extension points:
- drafting: Legal document drafting agent
"""

# Base interface
from src.agents.routers.base import BaseRouter

# Concrete routers
from src.agents.routers.conversational import ConversationalRouter
from src.agents.routers.rag import RAGRouter

# Classifier
from src.agents.routers.classifier import (
    Intent,
    QueryClassification,
    QueryClassifier,
    INTENT_TO_ROUTER,
)

# Registry
from src.agents.routers.registry import RouterRegistry

__all__ = [
    # Base
    "BaseRouter",
    # Routers
    "ConversationalRouter",
    "RAGRouter",
    # Classifier
    "Intent",
    "QueryClassification",
    "QueryClassifier",
    "INTENT_TO_ROUTER",
    # Registry
    "RouterRegistry",
]
