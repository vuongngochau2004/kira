"""Run isolated pipeline stages using the application's configured services."""

import os
import tempfile
from time import perf_counter
from typing import Any

from fastapi.encoders import jsonable_encoder
from loguru import logger

from src.config.config import settings
from src.modules.document.domain.services.extractor import extract_content
from src.modules.document.infrastructure.ocr.ocr_client import get_ocr_client
from src.modules.retrieval.domain.prompts.reranking import build_reranking_prompt
from src.modules.retrieval.domain.services.reranking.llm_reranker import (
    format_documents_for_reranking,
    parse_reranking_response,
    reorder_by_indices,
    run_llm_rerank,
)
from src.modules.retrieval.domain.services.reranking.tei_reranker import (
    rerank_documents_with_tei,
)
from src.modules.retrieval.domain.services.reranking_service import get_llm_client
from src.shared.kernel.di.registry import get_container
from src.shared.ports.classification import ClassificationStrategyBase
from src.shared.ports.ocr import OCRPort


async def inspect_document(content: bytes, suffix: str) -> dict[str, Any]:
    """Extract an image or PDF without adding it to document storage."""
    started = perf_counter()
    if suffix != "pdf":
        result = await get_ocr_client().ocr_image_bytes(content)
        return {
            "success": result.success,
            "text": result.text,
            "confidence": result.confidence,
            "metadata": {"extractor": "paddleocr", "raw_response": result.raw_response},
            "error": result.error,
            "latency_ms": round((perf_counter() - started) * 1000),
        }

    descriptor, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(content)
        container = await get_container()
        ocr = await container.get(OCRPort)
        result = await extract_content(path, "pdf", ocr=ocr)
        return {
            "success": result.success,
            "text": result.text,
            "pages": result.pages,
            "page_texts": result.page_texts,
            "metadata": jsonable_encoder(result.metadata),
            "error": result.error,
            "latency_ms": round((perf_counter() - started) * 1000),
        }
    finally:
        os.unlink(path)


async def inspect_classification(query: str, user_id: str) -> dict[str, Any]:
    """Classify with the same registered strategy chain used by chat."""
    started = perf_counter()
    container = await get_container()
    classifier = await container.get(ClassificationStrategyBase)
    result = await classifier.classify(query, user_id)
    return {
        **jsonable_encoder(result.to_dict()),
        "latency_ms": round((perf_counter() - started) * 1000),
    }


async def inspect_reranking(query: str, documents: list[str], top_k: int) -> dict[str, Any]:
    """Rerank supplied snippets using the configured RAG reranker."""
    started = perf_counter()
    candidates = [{"id": str(index + 1), "text": text} for index, text in enumerate(documents)]
    mode = settings.reranking_mode
    raw_response: str | None = None
    error: str | None = None
    if mode == "tei":
        results = await rerank_documents_with_tei(
            query,
            candidates,
            top_k=min(top_k, len(candidates)),
            timeout_seconds=settings.reranking_timeout_ms / 1000,
        )
        fallback = all("rerank_score" not in item for item in results)
    elif mode == "llm":
        llm_client = get_llm_client()
        if llm_client is None:
            raise RuntimeError("LLM reranker has not been initialized")
        prompt = build_reranking_prompt(query, format_documents_for_reranking(candidates))
        try:
            raw_response = await run_llm_rerank(
                llm_client, prompt, timeout_seconds=settings.reranking_timeout_ms / 1000
            )
            indices = parse_reranking_response(raw_response, len(candidates))
            results = reorder_by_indices(candidates, indices, min(top_k, len(candidates)))
            fallback = False
        except Exception as exc:
            logger.exception("Pipeline lab LLM reranking failed")
            results = candidates[:top_k]
            fallback = True
            error = str(exc)
    else:
        logger.warning("Unsupported reranking mode in pipeline lab: {}", mode)
        raise ValueError("Unsupported reranking mode")
    return {
        "mode": mode,
        "results": results,
        "fallback": fallback,
        "raw_response": raw_response,
        "error": error,
        "latency_ms": round((perf_counter() - started) * 1000),
    }
