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
from src.shared.ports.embedding import EmbeddingPort
from src.shared.ports.llm import LLMPort
from src.modules.retrieval.application.search_use_case import SearchUseCase


def create_default_rag_pipeline_service(
    *,
    embedding: EmbeddingPort | None = None,
    search: SearchUseCase | None = None,
    llm: LLMPort | None = None,
) -> RAGPipelineService:
    """Compose the default production RAG pipeline service."""
    pipeline = create_langgraph_pipeline(
        orchestrator_config=OrchestratorAgentConfig(),
        retrieval_config=RetrievalAgentConfig(),
        generation_config=GenerationAgentConfig(),
        quality_config=QualityAgentConfig(),
        embedding=embedding or EmbeddingAPIAdapter(),
        search=search or create_search_use_case(llm_client=llm),
        llm=llm or GLMAdapter(),
    )
    return RAGPipelineService(pipeline=pipeline)


__all__ = ["create_default_rag_pipeline_service"]
