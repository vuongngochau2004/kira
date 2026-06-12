"""RAG pipeline application service."""

from typing import AsyncIterator
from uuid import UUID

from src.modules.rag.orchestration.graph.langgraph_pipeline import LangGraphRAGPipeline
from src.modules.rag.orchestration.state.rag_state import RAGState


class RAGPipelineService:
    """Application service that runs the RAG domain pipeline."""

    def __init__(self, pipeline: LangGraphRAGPipeline):
        """Initialize with a composed domain pipeline."""
        self.pipeline = pipeline

    async def run(
        self,
        query: str,
        user_id: str,
        conversation_id: UUID | None = None,
    ) -> RAGState:
        """Run the RAG pipeline and return the final state."""
        return await self.pipeline.run(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
        )

    async def run_stream(
        self,
        query: str,
        user_id: str,
        conversation_id: UUID | None = None,
    ) -> AsyncIterator[dict]:
        """Stream updates from the RAG pipeline."""
        async for event in self.pipeline.run_stream(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
        ):
            yield event


__all__ = ["RAGPipelineService"]
