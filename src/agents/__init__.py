"""Agents module exports."""

# LLM
from src.agents.llm import chat_async

# Prompts
from src.agents.prompts import (
    STRATEGY_SELECTOR_PROMPT,
    CONTEXT_EVALUATOR_PROMPT,
    ANSWER_GENERATOR_PROMPT,
    CONVERSATIONAL_SYSTEM_PROMPT,
    CONVERSATIONAL_USER_PROMPT,
    CONVERSATIONAL_PROMPT,
    get_rag_template,
    ROUTING_CLASSIFIER_PROMPT,
)

# RAG Agent
from src.agents.rag_agent import AgenticRAG, generate_response, generate_response_simple

# Orchestrator
from src.agents.orchestrator import OrchestratorAgent, create_orchestrator

# Routers (multi-stage routing)
from src.agents.routers import (
    BaseRouter,
    ConversationalRouter,
    RAGRouter,
    Intent,
    QueryClassification,
    QueryClassifier,
    INTENT_TO_ROUTER,
    RouterRegistry,
)

# Utils
from src.agents.utils import is_conversational_query, parse_json_response, format_context

__all__ = [
    # LLM
    "chat_async",
    # Prompts
    "STRATEGY_SELECTOR_PROMPT",
    "CONTEXT_EVALUATOR_PROMPT",
    "ANSWER_GENERATOR_PROMPT",
    "CONVERSATIONAL_SYSTEM_PROMPT",
    "CONVERSATIONAL_USER_PROMPT",
    "CONVERSATIONAL_PROMPT",
    "ROUTING_CLASSIFIER_PROMPT",
    "get_rag_template",
    # RAG Agent
    "AgenticRAG",
    "generate_response",
    "generate_response_simple",
    # Orchestrator
    "OrchestratorAgent",
    "create_orchestrator",
    # Routers
    "BaseRouter",
    "ConversationalRouter",
    "RAGRouter",
    "Intent",
    "QueryClassification",
    "QueryClassifier",
    "INTENT_TO_ROUTER",
    "RouterRegistry",
    # Utils
    "is_conversational_query",
    "parse_json_response",
    "format_context",
]
