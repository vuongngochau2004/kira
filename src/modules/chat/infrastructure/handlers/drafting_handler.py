"""Administrative drafting handler for chat-driven document generation."""

import json
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, AsyncIterator

from loguru import logger

from src.config.config import settings
from src.modules.drafting.application.docx_renderer import render_administrative_docx
from src.modules.drafting.domain.prompts.administrative import build_administrative_drafting_prompt
from src.modules.retrieval.application.search_use_case import SearchUseCase
from src.modules.retrieval.composition import create_search_use_case
from src.shared.adapters.embedding.api_adapter import EmbeddingAPIAdapter
from src.shared.adapters.llm.glm_adapter import GLMAdapter
from src.shared.adapters.storage.minio_adapter import MinIOAdapter
from src.shared.domain.value_objects.citation import Citation
from src.shared.ports.classification import ClassificationResult, Intent
from src.shared.ports.embedding import EmbeddingPort
from src.shared.ports.handlers import HandlerConfig, HandlerResult, QueryHandlerBase
from src.shared.ports.llm import LLMPort
from src.shared.ports.storage import StoragePort


DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOWNLOAD_URL_TTL_SECONDS = 3600


class AdministrativeDraftingHandler(QueryHandlerBase):
    """Generate administrative document drafts from retrieved official materials."""

    def __init__(
        self,
        config: HandlerConfig | None = None,
        embedding: EmbeddingPort | None = None,
        search: SearchUseCase | None = None,
        llm: LLMPort | None = None,
        storage: StoragePort | None = None,
    ):
        """Initialize drafting handler dependencies."""
        self.config = config or HandlerConfig(max_retrieved_docs=8, max_tokens=3000, temperature=0.2)
        self.embedding = embedding or EmbeddingAPIAdapter()
        self.search = search or create_search_use_case()
        self.llm = llm or GLMAdapter()
        self.storage = storage or MinIOAdapter()

    async def handle(
        self,
        query: str,
        user_id: str | uuid.UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None,
    ) -> HandlerResult:
        """Generate a draft and a downloadable DOCX attachment."""
        if classification.intent != Intent.DRAFTING:
            raise ValueError(f"AdministrativeDraftingHandler cannot handle intent: {classification.intent}")

        t0 = time.perf_counter()
        try:
            documents = await self._retrieve_documents(query=query, user_id=str(user_id))
            if not documents:
                return HandlerResult(
                    content=(
                        "Tôi chưa tìm thấy tài liệu chính thức phù hợp để soạn văn bản này. "
                        "Vui lòng tải lên hoặc chọn tài liệu căn cứ trước khi yêu cầu soạn thảo."
                    ),
                    citations=[],
                    metadata={
                        "handler": self.get_name(),
                        "drafting": True,
                        "has_relevant_docs": False,
                    },
                )

            context_text = self._build_context(documents)
            prompt = build_administrative_drafting_prompt(query=query, context=context_text)
            raw_response = await self.llm.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            draft_result = self._parse_drafting_response(raw_response)
            if not draft_result["can_draft"]:
                latency_ms = (time.perf_counter() - t0) * 1000
                return HandlerResult(
                    content=self._build_insufficient_context_message(draft_result),
                    citations=[],
                    metadata={
                        "handler": self.get_name(),
                        "drafting": True,
                        "document_type": "administrative",
                        "has_relevant_docs": False,
                        "attachments": [],
                        "documents_used": 0,
                        "latency_ms": latency_ms,
                        "classification": classification.to_dict(),
                    },
                )

            content = draft_result["draft"]
            attachment = await self._create_attachment(content=content, query=query, user_id=str(user_id))
            citations = self._build_citations(documents)
            latency_ms = (time.perf_counter() - t0) * 1000

            return HandlerResult(
                content=content,
                citations=citations,
                metadata={
                    "handler": self.get_name(),
                    "drafting": True,
                    "document_type": "administrative",
                    "attachments": [attachment],
                    "documents_used": len(documents),
                    "latency_ms": latency_ms,
                    "classification": classification.to_dict(),
                },
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.error(f"Administrative drafting failed: {e}", exc_info=True)
            return HandlerResult(
                content="Có lỗi xảy ra khi soạn văn bản hành chính.",
                citations=[],
                metadata={
                    "handler": self.get_name(),
                    "drafting": True,
                    "error": str(e),
                    "latency_ms": latency_ms,
                },
                status="error",
                error=str(e),
            )

    async def handle_stream(
        self,
        query: str,
        user_id: str | uuid.UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict]:
        """Stream the generated draft and emit attachment metadata at the end."""
        if classification.intent != Intent.DRAFTING:
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": f"AdministrativeDraftingHandler cannot handle intent: {classification.intent}",
                    "handler": self.get_name(),
                },
            }
            return

        t0 = time.perf_counter()
        try:
            documents = await self._retrieve_documents(query=query, user_id=str(user_id))
            yield {
                "type": "retrieval",
                "data": {
                    "strategy": "Hybrid",
                    "docs_retrieved": len(documents),
                    "purpose": "administrative_drafting",
                },
            }

            if not documents:
                message = (
                    "Tôi chưa tìm thấy tài liệu chính thức phù hợp để soạn văn bản này. "
                    "Vui lòng tải lên hoặc chọn tài liệu căn cứ trước khi yêu cầu soạn thảo."
                )
                yield {"type": "content", "data": {"text": message}}
                yield {
                    "type": "metadata",
                    "data": {
                        "handler": self.get_name(),
                        "drafting": True,
                        "has_relevant_docs": False,
                        "citations": [],
                        "sources": [],
                    },
                }
                yield {"type": "done"}
                return

            context_text = self._build_context(documents)
            prompt = build_administrative_drafting_prompt(query=query, context=context_text)
            raw_response = await self.llm.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            draft_result = self._parse_drafting_response(raw_response)

            if not draft_result["can_draft"]:
                latency_ms = (time.perf_counter() - t0) * 1000
                yield {
                    "type": "content",
                    "data": {"text": self._build_insufficient_context_message(draft_result)},
                }
                yield {
                    "type": "metadata",
                    "data": {
                        "handler": self.get_name(),
                        "drafting": True,
                        "document_type": "administrative",
                        "has_relevant_docs": False,
                        "attachments": [],
                        "documents_used": 0,
                        "citations": [],
                        "sources": [],
                        "latency_ms": latency_ms,
                    },
                }
                yield {"type": "done"}
                return

            full_content = draft_result["draft"]
            yield {"type": "content", "data": {"text": full_content}}
            latency_ms = (time.perf_counter() - t0) * 1000

            attachment = await self._create_attachment(content=full_content, query=query, user_id=str(user_id))
            citations = [citation.to_dict() for citation in self._build_citations(documents)]

            yield {
                "type": "metadata",
                "data": {
                    "handler": self.get_name(),
                    "drafting": True,
                    "document_type": "administrative",
                    "attachments": [attachment],
                    "documents_used": len(documents),
                    "citations": citations,
                    "sources": citations,
                    "latency_ms": latency_ms,
                },
            }
            yield {"type": "done"}

        except Exception as e:
            logger.error(f"Administrative drafting stream failed: {e}", exc_info=True)
            yield {"type": "error", "data": {"error": str(e)}}
            yield {"type": "done"}

    async def _retrieve_documents(self, query: str, user_id: str) -> list[dict[str, Any]]:
        query_embedding = await self.embedding.embed(query)
        results = await self.search.execute(
            query_embedding=query_embedding,
            query_text=query,
            user_id=user_id,
            k=self.config.max_retrieved_docs,
            rrf_k=settings.rrf_k,
            enable_rerank=settings.reranking_enabled,
        )

        official_results = [
            result for result in results
            if (result.get("metadata") or {}).get("source_type") == "official"
        ]
        return official_results or results

    def _build_context(self, documents: list[dict[str, Any]]) -> str:
        parts = []
        for index, doc in enumerate(documents, start=1):
            metadata = doc.get("metadata") or {}
            filename = metadata.get("filename") or doc.get("filename") or f"Document {index}"
            page = metadata.get("page_number") or doc.get("page_number")
            source_label = f"[Document {index}] {filename}"
            if page:
                source_label += f" - page {page}"
            content = doc.get("content") or doc.get("text") or ""
            parts.append(f"{source_label}\n{content}")
        return "\n\n".join(parts)

    def _build_citations(self, documents: list[dict[str, Any]]) -> list[Citation]:
        citations: list[Citation] = []
        for index, doc in enumerate(documents, start=1):
            metadata = doc.get("metadata") or {}
            text = doc.get("content") or doc.get("text") or ""
            citations.append(
                Citation(
                    filename=metadata.get("filename") or doc.get("filename") or f"Document {index}",
                    page=metadata.get("page_number") or doc.get("page_number"),
                    text=text[:500],
                    confidence=float(doc.get("score", 1.0) or 1.0),
                    metadata={
                        "document_id": doc.get("document_id") or metadata.get("document_id"),
                        "chunk_index": doc.get("chunk_index") or metadata.get("chunk_index"),
                        "doc_index": index,
                    },
                )
            )
        return citations

    @staticmethod
    def _parse_drafting_response(response: str) -> dict[str, Any]:
        raw = (response or "").strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except json.JSONDecodeError:
                    parsed = {}
            else:
                lower = raw.lower()
                parsed = {"can_draft": lower.startswith("true"), "reason": raw}

        if isinstance(parsed, bool):
            parsed = {"can_draft": parsed}
        elif not isinstance(parsed, dict):
            parsed = {"can_draft": False, "reason": raw}

        draft = str(parsed.get("draft") or "").strip()
        can_draft = bool(parsed.get("can_draft", False)) and bool(draft)
        missing_info = parsed.get("missing_info") or []
        if not isinstance(missing_info, list):
            missing_info = [str(missing_info)]

        return {
            "can_draft": can_draft,
            "reason": str(parsed.get("reason") or "Tài liệu hiện có chưa đủ căn cứ để soạn thảo."),
            "missing_info": [str(item) for item in missing_info if str(item).strip()],
            "draft": draft,
        }

    @staticmethod
    def _build_insufficient_context_message(assessment: dict[str, Any]) -> str:
        lines = [
            "Tôi chưa thể soạn thảo văn bản hành chính cho yêu cầu này.",
            "",
            f"Lý do: {assessment['reason']}",
        ]
        missing_info = assessment.get("missing_info") or []
        if missing_info:
            lines.extend(["", "Thông tin cần bổ sung:"])
            lines.extend(f"{index}. {item}" for index, item in enumerate(missing_info, start=1))
        return "\n".join(lines)

    async def _create_attachment(self, content: str, query: str, user_id: str) -> dict[str, Any]:
        attachment_id = str(uuid.uuid4())
        filename = self._build_filename(query)
        storage_key = f"generated/{user_id}/{attachment_id}/{filename}"
        file_bytes = render_administrative_docx(content)
        download_url = await self.storage.upload(
            key=storage_key,
            data=file_bytes,
            content_type=DOCX_CONTENT_TYPE,
        )
        expires_at = datetime.utcnow() + timedelta(seconds=DOWNLOAD_URL_TTL_SECONDS)
        return {
            "id": attachment_id,
            "type": "administrative_document",
            "filename": filename,
            "content_type": DOCX_CONTENT_TYPE,
            "storage_key": storage_key,
            "download_url": download_url,
            "expires_at": expires_at.isoformat() + "Z",
        }

    @staticmethod
    def _build_filename(query: str) -> str:
        slug = query.lower()
        slug = re.sub(r"[^a-z0-9à-ỹđ\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug).strip("-")
        slug = slug[:80] or "van-ban-hanh-chinh"
        return f"{slug}.docx"

    def can_handle(self, classification: ClassificationResult) -> bool:
        """Return whether this handler supports the classified intent."""
        return classification.intent == Intent.DRAFTING

    def get_config(self) -> HandlerConfig:
        """Get handler configuration."""
        return self.config

    def get_name(self) -> str:
        """Get handler name."""
        return "AdministrativeDraftingHandler"


__all__ = ["AdministrativeDraftingHandler"]
