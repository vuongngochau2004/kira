"""Agentic RAG with self-evaluation and iterative retrieval."""

import sys
import asyncio
from pathlib import Path
from uuid import UUID
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents.llm import chat_async
from src.agents.prompts import ANSWER_GENERATOR_PROMPT
from src.agents.utils import format_context
from src.retrieval.hybrid import hybrid_search
from src.retrieval.dense import dense_search
from src.ingestion.embedding import embed_single
from src.ingestion.chunker import count_tokens
from src.ingestion.bm25_builder import get_bm25_manager
from config.config import settings
from src.constants import MAX_CONTEXT_TOKENS, MIN_CONTEXT_LENGTH

DEFAULT_MAX_ITERATIONS = 3
DEFAULT_RETRIEVAL_K = 5

SPECIFIC_TERMS = ["điều khoản", "khoản", "điều", "nghị định", "thông tư", "luật"]


class AgenticRAG:
    """Agentic RAG with self-evaluation and iterative retrieval."""

    def __init__(
        self,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        retrieval_k: int = DEFAULT_RETRIEVAL_K,
    ):
        """Initialize Agentic RAG.

        Args:
            max_iterations: Maximum retrieval iterations
            retrieval_k: Top-k chunks to retrieve per iteration
        """
        self.max_iterations = max_iterations
        self.retrieval_k = retrieval_k

    def select_strategy(self, query: str, bm25_available: bool = True) -> str:
        """Select retrieval strategy.

        Args:
            query: Query text
            bm25_available: Whether BM25 index is available

        Returns:
            Strategy: "dense" or "hybrid"
        """
        query_lower = query.lower()
        has_specific_terms = any(term in query_lower for term in SPECIFIC_TERMS)

        if has_specific_terms and bm25_available:
            return "hybrid"
        return "dense"

    async def retrieve(
        self,
        query: str,
        query_embedding: list[float],
        user_id: UUID | str,
        bm25_index: Any,
        strategy: str,
    ) -> list[dict]:
        """Retrieve documents.

        Args:
            query: Query text
            query_embedding: Query embedding vector
            user_id: User ID for filtering
            bm25_index: Optional BM25 index
            strategy: Retrieval strategy

        Returns:
            Retrieved documents
        """
        if strategy == "hybrid" and bm25_index:
            return hybrid_search(
                query_embedding=query_embedding,
                query_text=query,
                user_id=str(user_id),
                bm25_index=bm25_index,
                k=self.retrieval_k,
            )
        return dense_search(
            query_embedding=query_embedding,
            user_id=str(user_id),
            k=self.retrieval_k,
        )

    def evaluate_context(self, query: str, docs: list[dict]) -> bool:
        """Check if context is sufficient.

        Args:
            query: User query
            docs: Retrieved documents

        Returns:
            True if sufficient, False otherwise
        """
        if not docs:
            return False

        context = format_context(docs)
        return len(context) >= MIN_CONTEXT_LENGTH

    async def generate_answer(self, query: str, docs: list[dict]) -> str:
        """Generate answer from context.

        Args:
            query: User query
            docs: Retrieved documents

        Returns:
            Generated answer
        """
        prompt = ANSWER_GENERATOR_PROMPT.format(
            query=query,
            context=format_context(docs),
        )

        response = await chat_async(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
        )

        return response["content"]

    def build_rag_context(
        self,
        chunks: list[dict],
        max_tokens: int = MAX_CONTEXT_TOKENS,
    ) -> tuple[str, int]:
        """Build RAG context with token budgeting.

        Args:
            chunks: List of retrieved chunks
            max_tokens: Maximum context tokens

        Returns:
            (formatted_context, total_tokens)
        """
        selected_chunks = []
        total_tokens = 0

        for chunk in chunks:
            chunk_text = chunk.get("text", chunk.get("content", ""))
            chunk_tokens = count_tokens(chunk_text)

            if total_tokens + chunk_tokens > max_tokens:
                break

            selected_chunks.append(chunk)
            total_tokens += chunk_tokens

        return format_context(selected_chunks), total_tokens

    async def query(
        self,
        query: str,
        user_id: UUID | str,
        initial_strategy: str | None = None,
    ) -> dict[str, Any]:
        """Execute agentic RAG query.

        Args:
            query: User query
            user_id: User ID for filtering
            initial_strategy: Initial strategy or None for auto-select

        Returns:
            Dict with answer, retrieval_history, status
        """
        retrieval_history = []
        all_docs = []
        strategy = initial_strategy or self.select_strategy(query, True)

        query_embedding = await asyncio.to_thread(embed_single, query)
        bm25_manager = get_bm25_manager()
        bm25_index = bm25_manager.get_index(user_id)

        for iteration in range(self.max_iterations):
            docs = await self.retrieve(
                query=query,
                query_embedding=query_embedding,
                user_id=user_id,
                bm25_index=bm25_index if bm25_index and bm25_index.doc_freqs else None,
                strategy=strategy,
            )

            new_docs = self._deduplicate_docs(all_docs, docs)
            all_docs.extend(new_docs)

            sufficient = self.evaluate_context(query, all_docs)

            retrieval_history.append({
                "iteration": iteration + 1,
                "strategy": strategy,
                "docs_retrieved": len(docs),
                "new_docs": len(new_docs),
                "sufficient": sufficient,
            })

            if sufficient:
                answer = await self.generate_answer(query, all_docs)
                return self._build_success_response(answer, retrieval_history, all_docs, iteration + 1)

            strategy = self._switch_strategy(strategy, bm25_index)

        answer = await self.generate_answer(query, all_docs)
        return self._build_max_iterations_response(answer, retrieval_history, all_docs)

    def _deduplicate_docs(self, existing: list[dict], new: list[dict]) -> list[dict]:
        """Remove duplicate docs by chunk_id."""
        seen_ids = {d.get("chunk_id") for d in existing if d.get("chunk_id")}
        return [d for d in new if d.get("chunk_id") not in seen_ids]

    def _switch_strategy(self, current: str, bm25_index: Any) -> str:
        """Switch strategy for next iteration."""
        if current == "hybrid":
            return "dense"
        if current == "dense" and bm25_index and bm25_index.doc_freqs:
            return "hybrid"
        return "dense"

    def _build_success_response(
        self,
        answer: str,
        history: list,
        docs: list,
        iterations: int,
    ) -> dict:
        """Build success response."""
        return {
            "content": answer,
            "retrieval_history": history,
            "total_docs": len(docs),
            "iterations": iterations,
            "status": "success",
        }

    def _build_max_iterations_response(
        self,
        answer: str,
        history: list,
        docs: list,
    ) -> dict:
        """Build max iterations reached response."""
        return {
            "content": answer,
            "retrieval_history": history,
            "total_docs": len(docs),
            "iterations": self.max_iterations,
            "status": "max_iterations_reached",
        }


async def generate_response(
    query: str,
    user_id: UUID | str,
    conversation_history: list[dict] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    stream_callback: Any = None,
) -> dict:
    """Legacy: Generate RAG response.

    Args:
        query: User query
        user_id: User ID for filtering
        conversation_history: Optional conversation history
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        stream_callback: Optional streaming callback

    Returns:
        Response dict with content, citations, metadata
    """
    agent = AgenticRAG(max_iterations=1)
    result = await agent.query(query, user_id)

    return {
        "content": result["content"],
        "citations": [],
        "sources": [],
        "metadata": {
            "agent": "rag",
            "chunks_found": result["total_docs"],
        },
    }


async def generate_response_simple(
    query: str,
    context_chunks: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> dict:
    """Legacy: Generate RAG response from pre-retrieved chunks.

    Args:
        query: User query
        context_chunks: Pre-retrieved context chunks
        temperature: Sampling temperature
        max_tokens: Max tokens to generate

    Returns:
        Response dict with content and citations
    """
    if not context_chunks:
        return {
            "content": f"Không tìm thấy thông tin liên quan đến \"{query}\".",
            "citations": [],
            "metadata": {"agent": "rag", "chunks_found": 0},
        }

    prompt = ANSWER_GENERATOR_PROMPT.format(
        query=query,
        context=format_context(context_chunks),
    )

    response = await chat_async(
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return {
        "content": response["content"],
        "citations": [],
        "metadata": {
            "agent": "rag",
            "chunks_found": len(context_chunks),
        },
    }


__all__ = [
    "AgenticRAG",
    "generate_response",
    "generate_response_simple",
]
