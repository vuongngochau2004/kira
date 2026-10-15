"""LLM-based relative document re-ranking strategy."""

import asyncio
import json
import logging
import re
from typing import Any

from src.modules.retrieval.domain.prompts import (
    RERANKING_SYSTEM_PROMPT,
    build_reranking_prompt,
)

logger = logging.getLogger(__name__)


async def run_llm_rerank(llm_client: Any, prompt: str, timeout_seconds: float = 10.0) -> str:
    """Run LLM reranking prompt with timeout."""
    messages = [
        {"role": "system", "content": RERANKING_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    response = await asyncio.wait_for(
        llm_client.chat_async(
            messages=messages,
            temperature=0.1,
            max_tokens=256,
        ),
        timeout=timeout_seconds,
    )

    return response.get("content", "")


def format_documents_for_reranking(documents: list[dict]) -> str:
    """Format candidate documents for LLM reranking prompt."""
    formatted = []
    for idx, doc in enumerate(documents):
        text = doc.get("text", doc.get("content", ""))
        text_preview = text[:800] + "..." if len(text) > 800 else text
        formatted.append(f"[{idx}] {text_preview}")

    return "\n\n".join(formatted)


def parse_reranking_response(response: str, num_documents: int) -> list[int]:
    """Parse LLM response to extract ranked document indices."""
    try:
        json_match = re.search(r"\[.*?\]", response)
        if json_match:
            indices = json.loads(json_match.group(0))
            if isinstance(indices, list):
                return [int(i) for i in indices]
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug("Failed to parse JSON from response: %s", e)

    try:
        numbers = re.findall(r"\d+", response)
        if numbers:
            return [int(n) for n in numbers]
    except Exception as e:
        logger.warning("Failed to parse indices from response: %s", e)

    return list(range(num_documents))


def reorder_by_indices(
    candidates: list[dict],
    indices: list[int],
    top_k: int,
) -> list[dict]:
    """Reorder candidates by ranked indices with deduplication."""
    reranked = []
    seen = set()

    for idx in indices:
        if idx in seen or idx >= len(candidates) or idx < 0:
            continue
        reranked.append(candidates[idx])
        seen.add(idx)

    for idx, doc in enumerate(candidates):
        if idx not in seen and len(reranked) < top_k:
            reranked.append(doc)

    return reranked[:top_k]


async def rerank_documents_with_llm(
    query: str,
    candidates: list[dict],
    llm_client: Any,
    top_k: int = 5,
    timeout_seconds: float = 10.0,
) -> list[dict]:
    """Rerank candidate documents using LLM relative comparison.

    Args:
        query: User search query
        candidates: Retrieved document candidates
        llm_client: LLM client with chat_async method
        top_k: Number of documents to return
        timeout_seconds: LLM timeout

    Returns:
        List of reranked documents
    """
    if not candidates or len(candidates) <= top_k:
        return candidates

    formatted_docs = format_documents_for_reranking(candidates)
    prompt = build_reranking_prompt(query, formatted_docs)

    try:
        llm_response = await run_llm_rerank(llm_client, prompt, timeout_seconds=timeout_seconds)
        ranked_indices = parse_reranking_response(llm_response, len(candidates))
        reranked = reorder_by_indices(candidates, ranked_indices, top_k)
        logger.debug("Reranked %d documents from %d candidates", len(reranked), len(candidates))
        return reranked
    except Exception as e:
        logger.error("LLM reranking failed: %s", e)
        return candidates[:top_k]


__all__ = [
    "rerank_documents_with_llm",
    "run_llm_rerank",
    "format_documents_for_reranking",
    "parse_reranking_response",
    "reorder_by_indices",
]
