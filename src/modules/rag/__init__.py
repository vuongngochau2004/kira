"""RAG module - Multi-agent Retrieval-Augmented Generation bounded context.

This module encapsulates RAG-specific workflow code:
- Multi-agent orchestration (Orchestrator, Retrieval, Generation, Quality)
- LangGraph pipeline for agent coordination
- RAG State schema (TypedDict for LangGraph)
- RAG domain services (rejection detection, citation processing)

Primary exports:
    RAGPipelineService: Application service for running RAG workflows
    create_langgraph_pipeline: Factory for LangGraph RAG pipeline
    OrchestratorAgent, RetrievalAgent, GenerationAgent, QualityAgent
"""
from src.modules.rag.application import RAGPipelineService
from src.modules.rag.orchestration.graph.langgraph_pipeline import create_langgraph_pipeline
from src.modules.rag.orchestration.agents import (
    OrchestratorAgent,
    RetrievalAgent,
    GenerationAgent,
    QualityAgent,
)

__all__ = [
    "RAGPipelineService",
    "create_langgraph_pipeline",
    "OrchestratorAgent",
    "RetrievalAgent",
    "GenerationAgent",
    "QualityAgent",
]
