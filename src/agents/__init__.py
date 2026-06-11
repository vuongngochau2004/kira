"""
Agents Package - LLM, RAG, and 4-Agent Architecture

This package provides:
- LLM client abstraction (multi-provider)
- RAG agent with citations
- 4-agent architecture (Retrieval, Generation, Orchestrator, Quality)
- Citation parsing and verification
- Agent utilities and prompts

**Architecture**:
- 4-Agent System: retrieval → generation → quality → orchestrator
- Hybrid retrieval: Dense (Qdrant) + BM25 with RRF
- Citation system: Parser → Verifier → Formatter

**File Naming**: All files use kebab-case (e.g., `generation-agent.py`)

**Migration Notes**:
- Old router-based architecture removed (routers/ directory deleted)
- Legacy orchestrator.py removed (use orchestrator-agent.py instead)
- All imports updated to kebab-case filenames
"""

# =============================================================================
# LLM Client
# =============================================================================
from agents.llm import chat_async

# =============================================================================
# Prompts
# =============================================================================
from agents.prompts import (
    STRATEGY_SELECTOR_PROMPT,
    CONTEXT_EVALUATOR_PROMPT,
    ANSWER_GENERATOR_PROMPT,
    CONVERSATIONAL_SYSTEM_PROMPT,
    CONVERSATIONAL_USER_PROMPT,
    CONVERSATIONAL_PROMPT,
    get_rag_template,
    ROUTING_CLASSIFIER_PROMPT,
)

# =============================================================================
# RAG Agent (with citations)
# =============================================================================
from agents.rag_agent import AgenticRAG, generate_response, generate_response_simple

# =============================================================================
# 4-Agent Architecture (Agentic RAG)
# =============================================================================
from agents.retrieval_agent import RetrievalAgent
from agents.generation_agent import GenerationAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.quality_agent import QualityAgent

# =============================================================================
# Citation Handling
# =============================================================================
from agents.citation_parser import CitationParser, ParsedCitation
from agents.citation_verifier import (
    CitationVerifier,
    CitationCheck,
    CitationStatus,
)

# =============================================================================
# Post-Processing
# =============================================================================
from agents.llm_post_processor import stream_with_thinking_separation

# =============================================================================
# Utilities
# =============================================================================
from agents.agent_utils import (
    is_conversational_query,
    parse_json_response,
    format_context,
    CONVERSATIONAL_KEYWORDS,
)

__all__ = [
    # LLM Client
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

    # 4-Agent Architecture
    "RetrievalAgent",
    "GenerationAgent",
    "OrchestratorAgent",
    "QualityAgent",

    # Citation Handling
    "CitationParser",
    "ParsedCitation",
    "CitationVerifier",
    "CitationCheck",
    "CitationStatus",

    # Post-Processing
    "stream_with_thinking_separation",

    # Utilities
    "is_conversational_query",
    "parse_json_response",
    "format_context",
    "CONVERSATIONAL_KEYWORDS",
]
