"""Reranking service for LLM-based document reranking.

Provides LLM-based document reranking to improve retrieval precision
by scoring and reordering documents after initial retrieval.
"""

import asyncio
import json
import logging
import re
from typing import Any

from langchain_core.tools import tool

from src.config.config import settings
from src.modules.retrieval.domain.prompts import (
    RERANKING_SYSTEM_PROMPT,
    SCORING_SYSTEM_PROMPT,
    build_reranking_prompt,
    build_scoring_prompt,
)


logger = logging.getLogger(__name__)

# Global LLM client reference
_llm_client: Any = None


async def _run_llm_rerank(llm_client: Any, prompt: str) -> str:
    """Run LLM reranking with timeout.

    Args:
        llm_client: LLM client with chat_async method
        prompt: Reranking prompt

    Returns:
        LLM response content

    Raises:
        Exception: If LLM call fails or times out
    """
    messages = [
        {"role": "system", "content": RERANKING_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    response = await asyncio.wait_for(
        llm_client.chat_async(
            messages=messages,
            temperature=0.1,
            max_tokens=256,
        ),
        timeout=10,
    )

    return response.get("content", "")


async def _score_document_async(llm_client: Any, prompt: str) -> float:
    """Score a single document's relevance.

    Args:
        llm_client: LLM client
        prompt: Scoring prompt

    Returns:
        Relevance score (0.0-1.0)
    """
    messages = [
        {"role": "system", "content": SCORING_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    try:
        response = await llm_client.chat_async(
            messages=messages,
            temperature=0.1,
            max_tokens=50,
        )
        content = response.get("content", "0.0")

        # Extract float from response
        match = re.search(r'0?\.\d+|1\.0|0|1', content)
        if match:
            score = float(match.group(0))
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
        return 0.0
    except Exception as e:
        logger.debug(f"Failed to score document: {e}")
        return 0.0


async def _score_all_documents_async(
    llm_client: Any,
    query: str,
    doc_list: list[dict],
) -> list[dict]:
    """Score all documents in parallel.

    Args:
        llm_client: LLM client
        query: Search query
        doc_list: List of documents
    Returns:
        List of documents with rerank_score
    """
    tasks = []
    for doc in doc_list:
        text = doc.get("text", doc.get("content", "")) or ""
        prompt = build_scoring_prompt(query, text[:1000])
        tasks.append(_score_document_async(llm_client, prompt))

    scores = await asyncio.gather(*tasks)

    scored_docs = []
    for doc, score in zip(doc_list, scores):
        doc_copy = doc.copy()
        doc_copy["rerank_score"] = score
        scored_docs.append(doc_copy)

    return scored_docs


def init_reranking_service(llm_client: Any = None) -> None:
    """Initialize global LLM client for reranking.

    Args:
        llm_client: LLM client instance with chat_async method
    """
    global _llm_client
    _llm_client = llm_client


def _get_llm_client() -> Any:
    """Get the global LLM client instance.

    Returns:
        LLM client or None if not initialized
    """
    return _llm_client


def _format_documents_for_reranking(documents: list[dict]) -> str:
    """Format documents for LLM reranking prompt.

    Args:
        documents: List of document dicts with text/content field

    Returns:
        Formatted string for LLM prompt
    """
    formatted = []
    for idx, doc in enumerate(documents):
        text = doc.get("text", doc.get("content", ""))
        # Truncate very long documents to save tokens
        text_preview = text[:800] + "..." if len(text) > 800 else text
        formatted.append(f"[{idx}] {text_preview}")

    return "\n\n".join(formatted)


def _parse_reranking_response(
    response: str,
    num_documents: int
) -> list[int]:
    """Parse LLM response to extract ranked indices.

    Args:
        response: LLM response string
        num_documents: Number of documents to validate against

    Returns:
        List of ranked indices

    Examples:
        >>> _parse_reranking_response("[3, 0, 2, 1]", 4)
        [3, 0, 2, 1]
        >>> _parse_reranking_response("3,0,2,1", 4)
        [3, 0, 2, 1]
    """
    # Try to extract JSON array
    try:
        # Clean response - find JSON array
        json_match = re.search(r'\[.*?\]', response)
        if json_match:
            indices = json.loads(json_match.group(0))
            if isinstance(indices, list):
                return [int(i) for i in indices]
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug(f"Failed to parse JSON from response: {e}")

    # Fallback: extract comma-separated numbers
    try:
        numbers = re.findall(r'\d+', response)
        if numbers:
            return [int(n) for n in numbers]
    except Exception as e:
        logger.warning(f"Failed to parse indices from response: {e}")

    # Last resort: return original order
    return list(range(num_documents))


@tool
def llm_rerank(
    query: str,
    documents: str,
    top_k: int = 5,
) -> str:
    """Rerank documents using LLM to improve relevance.

    Use this tool AFTER initial retrieval to improve precision.
    The LLM analyzes the query and each document to determine
    which documents are most relevant.

    Args:
        query: The user's search query
        documents: JSON string of retrieved documents to rerank.
                   Each document should have 'text' or 'content' field.
        top_k: Number of top documents to return after reranking

    Returns:
        JSON string of reranked documents with updated order

    Example:
        >>> docs = [{"text": "doc1", "metadata": {}}, {"text": "doc2", "metadata": {}}]
        >>> result = llm_rerank.invoke({"query": "search query", "documents": json.dumps(docs), "top_k": 3})
        >>> reranked = json.loads(result)
    """
    try:
        # Parse documents
        doc_list = json.loads(documents)
        if not doc_list:
            return json.dumps([], ensure_ascii=False)

        num_docs = len(doc_list)
        if num_docs <= top_k:
            # No need to rerank if we already have few docs
            return documents

        # Format for LLM
        formatted_docs = _format_documents_for_reranking(doc_list)

        # Create reranking prompt
        prompt = build_reranking_prompt(query, formatted_docs)

        # Call LLM
        llm_client = _get_llm_client()
        if llm_client is None:
            logger.warning("LLM client not initialized, returning original order")
            return json.dumps(doc_list[:top_k], ensure_ascii=False)

        # Run async LLM call in sync context
        llm_response = asyncio.run(_run_llm_rerank(llm_client, prompt))

        # Parse response
        ranked_indices = _parse_reranking_response(llm_response, num_docs)

        # Validate and reorder documents
        reranked = []
        seen = set()

        for idx in ranked_indices:
            if idx in seen or idx >= num_docs or idx < 0:
                continue
            reranked.append(doc_list[idx])
            seen.add(idx)

        # Add any missed documents (shouldn't happen with valid response)
        for idx, doc in enumerate(doc_list):
            if idx not in seen and len(reranked) < top_k:
                reranked.append(doc)

        logger.debug(f"Reranked {len(reranked)} documents from {num_docs} candidates")

        return json.dumps(reranked[:top_k], ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in llm_rerank: {e}", exc_info=True)
        # Return original documents on error
        try:
            doc_list = json.loads(documents)
            return json.dumps(doc_list[:top_k], ensure_ascii=False)
        except:
            return json.dumps([], ensure_ascii=False)


@tool
def score_and_rerank(
    query: str,
    documents: str,
    top_k: int = 5,
    min_score_threshold: float = 0.3,
) -> str:
    """Score documents individually and rerank by relevance score.

    Unlike llm_rerank which ranks by relative comparison, this tool
    scores each document independently on a 0-1 scale, then filters
    and reranks by score.

    Args:
        query: The user's search query
        documents: JSON string of retrieved documents to score
        top_k: Number of top documents to return
        min_score_threshold: Minimum relevance score (0-1) to keep

    Returns:
        JSON string of scored and reranked documents

    Example:
        >>> docs = [{"text": "relevant doc"}, {"text": "unrelated"}]
        >>> result = score_and_rerank.invoke({"query": "search", "documents": json.dumps(docs)})
        >>> scored = json.loads(result)
        >>> scored[0].get("rerank_score")  # e.g., 0.85
    """
    try:
        doc_list = json.loads(documents)
        if not doc_list:
            return json.dumps([], ensure_ascii=False)

        num_docs = len(doc_list)

        llm_client = _get_llm_client()
        if llm_client is None:
            logger.warning("LLM client not initialized, returning original order")
            return json.dumps(doc_list[:top_k], ensure_ascii=False)

        # Run async scoring
        try:
            scored_docs = asyncio.run(
                _score_all_documents_async(llm_client, query, doc_list)
            )
        except Exception as e:
            logger.error(f"Async scoring failed: {e}")
            scored_docs = [{**doc, "rerank_score": 0.0} for doc in doc_list]

        # Filter by threshold and sort by score
        filtered = [
            doc for doc in scored_docs
            if doc.get("rerank_score", 0) >= min_score_threshold
        ]

        reranked = sorted(filtered, key=lambda x: x.get("rerank_score", 0), reverse=True)

        logger.debug(f"Scored {num_docs} docs, {len(filtered)} passed threshold")

        return json.dumps(reranked[:top_k], ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in score_and_rerank: {e}", exc_info=True)
        try:
            doc_list = json.loads(documents)
            return json.dumps(doc_list[:top_k], ensure_ascii=False)
        except:
            return json.dumps([], ensure_ascii=False)


__all__ = [
    "init_reranking_service",
    "llm_rerank",
    "score_and_rerank",
]
