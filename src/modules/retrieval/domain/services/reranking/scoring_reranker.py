"""LLM-based individual document scoring and threshold reranking strategy."""

import asyncio
import logging
import re
from typing import Any

from src.modules.retrieval.domain.prompts import (
    SCORING_SYSTEM_PROMPT,
    build_scoring_prompt,
)

logger = logging.getLogger(__name__)


async def score_document_async(llm_client: Any, prompt: str) -> float:
    """Score a single document's relevance (0.0 to 1.0)."""
    messages = [
        {"role": "system", "content": SCORING_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    try:
        response = await llm_client.chat_async(
            messages=messages,
            temperature=0.1,
            max_tokens=50,
        )
        content = response.get("content", "0.0")

        match = re.search(r"0?\.\d+|1\.0|0|1", content)
        if match:
            score = float(match.group(0))
            return max(0.0, min(1.0, score))
        return 0.0
    except Exception as e:
        logger.debug("Failed to score document: %s", e)
        return 0.0


async def score_all_documents_async(
    llm_client: Any,
    query: str,
    doc_list: list[dict],
) -> list[dict]:
    """Score all documents in parallel and attach rerank_score."""
    tasks = []
    for doc in doc_list:
        text = doc.get("text", doc.get("content", "")) or ""
        prompt = build_scoring_prompt(query, text[:1000])
        tasks.append(score_document_async(llm_client, prompt))

    scores = await asyncio.gather(*tasks)

    scored_docs = []
    for doc, score in zip(doc_list, scores, strict=False):
        doc_copy = doc.copy()
        doc_copy["rerank_score"] = score
        scored_docs.append(doc_copy)

    return scored_docs


async def score_and_filter_documents(
    query: str,
    candidates: list[dict],
    llm_client: Any,
    top_k: int = 5,
    min_score_threshold: float = 0.3,
) -> list[dict]:
    """Score each candidate document independently, filter by threshold, and sort descending.

    Args:
        query: User query
        candidates: Candidate documents
        llm_client: LLM client instance
        top_k: Max results to return
        min_score_threshold: Minimum relevance score to keep

    Returns:
        List of scored and filtered documents sorted by relevance
    """
    if not candidates:
        return []

    try:
        scored_docs = await score_all_documents_async(llm_client, query, candidates)
    except Exception as e:
        logger.error("Async document scoring failed: %s", e)
        scored_docs = [{**doc, "rerank_score": 0.0} for doc in candidates]

    filtered = [doc for doc in scored_docs if doc.get("rerank_score", 0) >= min_score_threshold]
    reranked = sorted(filtered, key=lambda x: x.get("rerank_score", 0), reverse=True)

    logger.debug("Scored %d docs, %d passed threshold", len(candidates), len(filtered))
    return reranked[:top_k]


__all__ = [
    "score_and_filter_documents",
    "score_document_async",
    "score_all_documents_async",
]
