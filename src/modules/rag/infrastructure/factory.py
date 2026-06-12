"""Infrastructure composition for the RAG module."""

from src.modules.rag.application import RAGPipelineService
from src.modules.rag.orchestration.graph.langgraph_pipeline import create_langgraph_pipeline
from src.modules.rag.orchestration.state.rag_state import (
    GenerationAgentConfig,
    OrchestratorAgentConfig,
    QualityAgentConfig,
    RetrievalAgentConfig,
)
from src.modules.retrieval.composition import create_search_use_case
from src.shared.adapters.embedding.api_adapter import EmbeddingAPIAdapter
from src.shared.adapters.llm.glm_adapter import GLMAdapter


def create_default_rag_pipeline_service() -> RAGPipelineService:
    """Compose the default production RAG pipeline service."""
    pipeline = create_langgraph_pipeline(
        orchestrator_config=OrchestratorAgentConfig(),
        retrieval_config=RetrievalAgentConfig(),
        generation_config=GenerationAgentConfig(),
        quality_config=QualityAgentConfig(),
        embedding=EmbeddingAPIAdapter(),
        search=create_search_use_case(),
        llm=GLMAdapter(),
    )
    return RAGPipelineService(pipeline=pipeline)


__all__ = ["create_default_rag_pipeline_service"]
