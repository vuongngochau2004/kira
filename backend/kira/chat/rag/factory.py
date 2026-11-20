"""Infrastructure composition for the RAG module."""

from kira.chat.rag.graph import create_langgraph_pipeline
from kira.chat.rag.pipeline import RAGPipelineService
from kira.chat.rag.state import (
    GenerationAgentConfig,
    OrchestratorAgentConfig,
    QualityAgentConfig,
    RetrievalAgentConfig,
)
from kira.config import settings
from kira.providers.embedding.base import EmbeddingPort
from kira.providers.embedding.factory import create_embedding_adapter
from kira.providers.llm.adapter import GLMAdapter
from kira.providers.llm.base import LLMPort
from kira.providers.llm.traced import TracedLLMPort
from kira.retrieval.composition import create_search_use_case
from kira.retrieval.search import SearchUseCase


def create_default_rag_pipeline_service(
    *,
    embedding: EmbeddingPort | None = None,
    search: SearchUseCase | None = None,
    llm: LLMPort | None = None,
) -> RAGPipelineService:
    """Compose the default production RAG pipeline service."""
    traced_llm = TracedLLMPort(llm or GLMAdapter())
    pipeline = create_langgraph_pipeline(
        orchestrator_config=OrchestratorAgentConfig(),
        retrieval_config=RetrievalAgentConfig(
            top_k=max(settings.retrieval_k, settings.reranking_top_k_before),
            rerank_top_k=settings.reranking_top_k_after,
            rerank_threshold=settings.reranking_min_score_threshold,
            reranker_model=settings.reranking_mode,
        ),
        generation_config=GenerationAgentConfig(),
        quality_config=QualityAgentConfig(),
        embedding=embedding or create_embedding_adapter(),
        search=search or create_search_use_case(llm_client=traced_llm),
        llm=traced_llm,
    )
    return RAGPipelineService(pipeline=pipeline)


__all__ = ["create_default_rag_pipeline_service"]
