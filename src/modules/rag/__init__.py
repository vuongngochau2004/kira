"""RAG module — Multi-agent Retrieval-Augmented Generation Bounded Context.

This module encapsulates all RAG-specific domain logic:
- Multi-agent orchestration (Orchestrator, Retrieval, Generation, Quality)
- LangGraph pipeline for agent coordination
- RAG State schema (TypedDict for LangGraph)
- RAG domain services (rejection detection, citation processing)

Primary exports:
    create_langgraph_pipeline: Factory for LangGraph RAG pipeline
    OrchestratorAgent, RetrievalAgent, GenerationAgent, QualityAgent
"""
from src.modules.rag.domain.graph.langgraph_pipeline import create_langgraph_pipeline
from src.modules.rag.domain.agents import (
    OrchestratorAgent,
    RetrievalAgent,
    GenerationAgent,
    QualityAgent,
)

__all__ = [
    "create_langgraph_pipeline",
    "OrchestratorAgent",
    "RetrievalAgent",
    "GenerationAgent",
    "QualityAgent",
]
