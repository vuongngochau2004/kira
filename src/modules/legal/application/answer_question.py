"""Answer a legal question with provisions in force on the resolved date(s)."""

import logging
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from src.modules.legal.application.ports import (
    LegalKeywordSearchPort,
    LegalProvisionSearchPort,
    LegalRerankerPort,
)
from src.modules.legal.application.temporal import ResolveTemporalQuery
from src.modules.legal.domain.prompts.legal_qa import (
    GRAPH_UNAVAILABLE_NOTICE,
    build_legal_qa_messages,
    citation_payload,
    not_found_message,
)
from src.modules.legal.domain.qa import LegalSource, ProvisionHit, fuse_hits
from src.modules.legal.domain.temporal import TemporalQuery
from src.shared.ports.embedding import EmbeddingPort
from src.shared.ports.legal_graph import LegalGraphPort, ProvisionContext
from src.shared.ports.llm import LLMPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LegalQAStatus:
    stage: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LegalQAToken:
    text: str


@dataclass(frozen=True)
class LegalQAResult:
    temporal: TemporalQuery
    citations: list[dict[str, Any]]
    notices: list[str]


LegalQAEvent = LegalQAStatus | LegalQAToken | LegalQAResult


@dataclass(frozen=True)
class LegalQAOptions:
    seed_top_k: int = 20
    final_top_k: int = 8
    max_guides: int = 5
    snippet_length: int = 900
    min_score: float = 0.0


class AnswerLegalQuestion:
    def __init__(
        self,
        temporal: ResolveTemporalQuery,
        embedding: EmbeddingPort,
        search: LegalProvisionSearchPort,
        keywords: LegalKeywordSearchPort,
        graph: LegalGraphPort,
        reranker: LegalRerankerPort,
        llm: LLMPort,
        options: LegalQAOptions,
    ) -> None:
        self._temporal = temporal
        self._embedding = embedding
        self._search = search
        self._keywords = keywords
        self._graph = graph
        self._reranker = reranker
        self._llm = llm
        self._options = options

    async def stream(self, question: str) -> AsyncIterator[LegalQAEvent]:
        temporal = await self._temporal.execute(question)
        yield LegalQAStatus(
            "temporal",
            {
                "mode": temporal.mode,
                "dates": [day.isoformat() for day in temporal.dates],
                "source": temporal.source,
            },
        )
        vector = await self._embedding.embed(question)
        notices: list[str] = []
        if temporal.mode == "compare":
            sources = await self._compare_sources(question, vector, temporal, notices)
        else:
            sources = await self._single_sources(question, vector, temporal.dates[0], notices)
        yield LegalQAStatus("retrieval", {"sources": len(sources)})

        if not sources:
            yield LegalQAToken(not_found_message(temporal))
            yield LegalQAResult(temporal, [], notices)
            return

        messages = build_legal_qa_messages(question, temporal, sources, notices)
        async for chunk in self._llm.stream(messages, temperature=0.1, max_tokens=1500):
            if chunk:
                yield LegalQAToken(chunk)
        citations = [citation_payload(source, self._options.snippet_length) for source in sources]
        yield LegalQAResult(temporal, citations, notices)

    async def _seeds(self, question: str, vector: Sequence[float], day: date) -> list[ProvisionHit]:
        dense = await self._search.search_in_force(
            vector, day, self._options.seed_top_k, min_score=self._options.min_score
        )
        if not dense:
            # Keyword matches alone are too weak to claim a relevant provision exists.
            return []
        try:
            lexical = await self._keywords.search(question, day, self._options.seed_top_k)
        except Exception as exc:  # BM25 is a recall booster; dense search alone still answers
            logger.warning("Legal keyword search failed: %s", exc)
            lexical = []
        return fuse_hits([dense, lexical])[: self._options.seed_top_k]

    async def _single_sources(
        self, question: str, vector: Sequence[float], day: date, notices: list[str]
    ) -> list[LegalSource]:
        seeds = await self._seeds(question, vector, day)
        if not seeds:
            return []
        keys = list(dict.fromkeys(hit.provision_key for hit in seeds))
        contexts: dict[str, ProvisionContext] = {}
        guides: list[ProvisionHit] = []
        try:
            contexts = await self._graph.expand_context(keys, day)
            numbers = await self._graph.guiding_documents(keys)
            if numbers:
                guides = await self._search.search_in_force(
                    vector,
                    day,
                    self._options.max_guides,
                    numbers=numbers,
                    min_score=self._options.min_score,
                )
        except Exception as exc:  # answer from seeds; tell the user what was not checked
            logger.warning("Legal graph expansion failed: %s", exc)
            notices.append(GRAPH_UNAVAILABLE_NOTICE)

        ranked = await self._reranker.rerank(question, seeds, self._options.final_top_k)
        chosen = {hit.version_id for hit in ranked}
        sources = [_with_context(hit, contexts.get(hit.provision_key)) for hit in ranked]
        sources += [
            LegalSource(hit=guide, role="guide")
            for guide in guides
            if guide.version_id not in chosen
        ]
        return sources

    async def _compare_sources(
        self,
        question: str,
        vector: Sequence[float],
        temporal: TemporalQuery,
        notices: list[str],
    ) -> list[LegalSource]:
        before_day, after_day = temporal.dates
        seeds = fuse_hits(
            [
                await self._seeds(question, vector, after_day),
                await self._seeds(question, vector, before_day),
            ]
        )
        if not seeds:
            return []
        ranked = await self._reranker.rerank(question, seeds, self._options.final_top_k)
        keys = list(dict.fromkeys(hit.provision_key for hit in ranked))
        before = {
            hit.provision_key: hit
            for hit in await self._search.search_in_force(
                vector, before_day, len(keys), provision_keys=keys
            )
        }
        after = {
            hit.provision_key: hit
            for hit in await self._search.search_in_force(
                vector, after_day, len(keys), provision_keys=keys
            )
        }
        contexts: dict[str, ProvisionContext] = {}
        try:
            contexts = await self._graph.expand_context(keys, after_day)
        except Exception as exc:
            logger.warning("Legal graph expansion failed: %s", exc)
            notices.append(GRAPH_UNAVAILABLE_NOTICE)

        sources: list[LegalSource] = []
        for key in keys:
            old, new = before.get(key), after.get(key)
            if old is not None and new is not None and old.version_id == new.version_id:
                sources.append(LegalSource(hit=new))
                continue
            if old is not None:
                sources.append(LegalSource(hit=old, role="before" if new else "removed"))
            if new is not None:
                context = contexts.get(key)
                sources.append(
                    LegalSource(
                        hit=new,
                        role="after" if old else "added",
                        introduced_by_number=context.introduced_by_number if context else None,
                        introduced_by_title=context.introduced_by_title if context else None,
                    )
                )
        return sources


def _with_context(hit: ProvisionHit, context: ProvisionContext | None) -> LegalSource:
    if context is None:
        return LegalSource(hit=hit)
    return LegalSource(
        hit=hit,
        parent_label=context.parent_label,
        parent_text=context.parent_text,
        amended_after=context.amended_after,
        introduced_by_number=context.introduced_by_number,
        introduced_by_title=context.introduced_by_title,
    )
