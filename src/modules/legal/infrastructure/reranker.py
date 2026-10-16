"""Rerank legal provision hits with the configured KIRA reranker (TEI or LLM)."""

import logging
from collections.abc import Callable, Sequence
from typing import Any

from src.modules.legal.application.ports import LegalRerankerPort
from src.modules.legal.domain.qa import ProvisionHit
from src.modules.retrieval.domain.services.reranking.llm_reranker import rerank_documents_with_llm

logger = logging.getLogger(__name__)


class ConfiguredLegalReranker(LegalRerankerPort):
    def __init__(self, enabled: bool, mode: str, llm_client_provider: Callable[[], Any]) -> None:
        self._enabled = enabled
        self._mode = mode
        self._llm_client_provider = llm_client_provider

    async def rerank(
        self, query: str, hits: Sequence[ProvisionHit], top_k: int
    ) -> list[ProvisionHit]:
        ordered = list(hits)
        if not self._enabled or len(ordered) <= 1:
            return ordered[:top_k]
        candidates = [
            {"text": hit.text, "content": hit.text, "legal_index": index}
            for index, hit in enumerate(ordered)
        ]
        try:
            ranked = await self._rank(query, candidates, top_k)
        except Exception as exc:  # reranking only improves order; never fail the answer
            logger.warning("Legal reranking failed, keeping retrieval order: %s", exc)
            return ordered[:top_k]
        if ranked is None:
            return ordered[:top_k]
        result = [ordered[item["legal_index"]] for item in ranked if "legal_index" in item]
        return result[:top_k] or ordered[:top_k]

    async def _rank(
        self, query: str, candidates: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]] | None:
        if self._mode == "tei":
            from src.modules.retrieval.domain.services.reranking import tei_reranker

            return await tei_reranker.rerank_documents_with_tei(query, candidates, top_k=top_k)
        client = self._llm_client_provider()
        if client is None:
            return None
        return await rerank_documents_with_llm(query, candidates, client, top_k=top_k)
