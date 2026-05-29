"""Router registry for multi-stage query routing."""

import time
import logging
import re
import unicodedata
from uuid import UUID
from typing import Any, AsyncIterator

from src.agents.routers.base import BaseRouter
from src.agents.routers.classifier import (
    QueryClassifier,
    INTENT_TO_ROUTER,
)

logger = logging.getLogger(__name__)


class RouterRegistry:
    """Registry for managing and routing queries to appropriate routers.

    Multi-stage routing strategy:
    1. Quick Filter: Check all routers with can_handle() > QUICK_THRESHOLD
    2. LLM Classification: If no quick match, use LLM classifier
    3. Intent-based Routing: Map classified intent to router
    4. Fallback: Use default router if all else fails
    """

    QUICK_THRESHOLD = 0.8  # Confidence threshold for quick routing
    CLASSIFIER_THRESHOLD = 0.6  # Confidence threshold for LLM classification
    DEFAULT_ROUTER = "RAGRouter"

    _routers: dict[str, BaseRouter] = {}
    _classifier: QueryClassifier | None = None

    @classmethod
    def register(cls, router: BaseRouter, name: str | None = None) -> None:
        """Register a router.

        Args:
            router: Router instance to register
            name: Optional name (defaults to router class name)
        """
        router_name = name or router.get_name()
        cls._routers[router_name] = router
        logger.info(f"Registered router: {router_name}")

    @classmethod
    def get_router(cls, name: str) -> BaseRouter | None:
        """Get registered router by name.

        Args:
            name: Router name

        Returns:
            Router instance or None if not found
        """
        return cls._routers.get(name)

    @classmethod
    def set_classifier(cls, classifier: QueryClassifier) -> None:
        """Set the LLM classifier.

        Args:
            classifier: QueryClassifier instance
        """
        cls._classifier = classifier

    @classmethod
    async def route(
        cls,
        query: str,
        user_id: str | UUID = "default",
    ) -> dict[str, Any]:
        """Route query to appropriate router using multi-stage strategy.

        Args:
            query: User query
            user_id: User ID for filtering

        Returns:
            Response dict from selected router
        """
        t0 = time.perf_counter()

        # Stage 1: Quick Filter - keyword-based confidence check
        quick_result = await cls._quick_filter(query, user_id)
        if quick_result is not None:
            logger.info(f"Quick routed to: {quick_result.get('metadata', {}).get('router')}")
            return quick_result

        # Stage 2: LLM Classification
        if cls._classifier is None:
            cls._classifier = QueryClassifier()

        logger.info("No quick match, using LLM classifier...")
        classification = await cls._classifier.classify(query)

        # Stage 3: Intent-based Routing
        router_name = INTENT_TO_ROUTER.get(
            classification.intent,
            cls.DEFAULT_ROUTER
        )

        router = cls._routers.get(router_name)
        if not router:
            logger.warning(f"Router not found: {router_name}, using default")
            router = cls._routers.get(cls.DEFAULT_ROUTER)

        if not router:
            return cls._error_response("No routers available")

        # Check classification confidence
        if classification.confidence < cls.CLASSIFIER_THRESHOLD:
            logger.warning(
                f"Low confidence ({classification.confidence}): {classification.reason}"
            )

        # Stage 4: Execute Router
        try:
            result = await router.handle(query, user_id)
            result["latency_ms"] = (time.perf_counter() - t0) * 1000
            result.setdefault("metadata", {})["classification"] = {
                "intent": classification.intent,
                "confidence": classification.confidence,
                "reason": classification.reason,
            }
            return result
        except Exception as e:
            logger.error(f"Router {router_name} error: {e}")
            return cls._error_response(str(e))

    @classmethod
    async def route_stream(
        cls,
        query: str,
        user_id: str | UUID = "default",
    ) -> AsyncIterator[dict]:
        """Route query to appropriate router with streaming response.

        Args:
            query: User query
            user_id: User ID for filtering

        Yields:
            Dict chunks with type:
            - "routing": {router, intent, confidence}
            - "retrieval": {iteration, strategy, docs_retrieved, new_docs, sufficient}
            - "content": {text}
            - "metadata": {status, citations, sources, latency_ms}
        """
        t0 = time.perf_counter()

        # Stage 1: Quick Filter
        quick_router = await cls._quick_filter_router(query, user_id)

        if quick_router:
            logger.info(f"Quick routed to: {quick_router.get_name()}")
            yield {
                "type": "routing",
                "data": {
                    "router": quick_router.get_name(),
                    "method": "quick_filter",
                },
            }
            async for chunk in quick_router.handle_stream(query, user_id):
                yield chunk
            return

        # Stage 2: LLM Classification
        if cls._classifier is None:
            cls._classifier = QueryClassifier()

        logger.info("No quick match, using LLM classifier...")
        classification = await cls._classifier.classify(query)

        # Stage 3: Intent-based Routing
        router_name = INTENT_TO_ROUTER.get(
            classification.intent,
            cls.DEFAULT_ROUTER
        )

        router = cls._routers.get(router_name)
        if not router:
            logger.warning(f"Router not found: {router_name}, using default")
            router = cls._routers.get(cls.DEFAULT_ROUTER)

        if not router:
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": "No routers available",
                },
            }
            return

        # Emit routing info
        yield {
            "type": "routing",
            "data": {
                "router": router.get_name(),
                "intent": classification.intent,
                "confidence": classification.confidence,
                "method": "llm_classification",
            },
        }

        # Stage 4: Execute Router with streaming
        try:
            async for chunk in router.handle_stream(query, user_id):
                yield chunk

        except Exception as e:
            logger.error(f"Router {router_name} error: {e}")
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": str(e),
                    "router": router.get_name(),
                },
            }

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text by removing accents, lowercasing and cleaning spaces."""
        text = text.lower().strip()
        # Normalize unicode accents
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        # Replace Vietnamese dd -> d
        text = text.replace('đ', 'd')
        # Remove all non-alphanumeric/non-space/non-hyphen characters
        text = re.sub(r'[^\w\s-]', '', text)
        # Collapse extra spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @classmethod
    async def _quick_filter_router(
        cls,
        query: str,
        user_id: str | UUID = "default",
    ) -> BaseRouter | None:
        """Quick filter stage - find router with high confidence using DB matching and keywords.

        Args:
            query: User query
            user_id: User ID

        Returns:
            Best matching router or None
        """
        # 1. Option 4: Fuzzy File-Match and Active Document Keyword Matching
        if user_id and user_id != "default":
            try:
                from uuid import UUID as uuid_class
                if isinstance(user_id, str):
                    try:
                        user_uuid = uuid_class(user_id)
                    except ValueError:
                        user_uuid = None
                else:
                    user_uuid = user_id

                if user_uuid:
                    from src.database.session import async_session_factory
                    from src.indexing.document_store import list_documents
                    
                    async with async_session_factory() as session:
                        docs, count = await list_documents(user_id=user_uuid, db=session)
                        
                        if count > 0:
                            # Step A: Fuzzy matching of filename stem against normalized query
                            norm_query = cls._normalize_text(query)
                            for doc in docs:
                                if doc.status != "deleted" and doc.filename:
                                    from pathlib import Path
                                    stem = Path(doc.filename).stem
                                    norm_stem = cls._normalize_text(stem)
                                    if len(norm_stem) >= 3 and norm_stem in norm_query:
                                        logger.info(f"Fuzzy file match found: {doc.filename} in query. Routing to RAGRouter.")
                                        rag_router = cls._routers.get("RAGRouter")
                                        if rag_router:
                                            return rag_router

                            # Step B: General file keyword match if user has at least 1 document uploaded
                            file_keywords = ["file", "tài liệu", "tập tin", "doc", "docx", "pdf", "txt", "đính kèm", "trích dẫn"]
                            query_lower = query.lower()
                            if any(kw in query_lower for kw in file_keywords):
                                logger.info(f"File keyword match with active user documents. Routing to RAGRouter.")
                                rag_router = cls._routers.get("RAGRouter")
                                if rag_router:
                                    return rag_router
            except Exception as e:
                logger.error(f"Error in quick filter fuzzy file matching: {e}", exc_info=True)

        # 2. General Confidence-based Matching
        best_router: BaseRouter | None = None
        best_score = 0.0

        for router in cls._routers.values():
            score = await router.can_handle(query)
            if score > best_score and score >= cls.QUICK_THRESHOLD:
                best_score = score
                best_router = router

        return best_router

    @classmethod
    async def _quick_filter(
        cls,
        query: str,
        user_id: str | UUID,
    ) -> dict[str, Any] | None:
        """Quick filter stage - check routers with high confidence.

        Args:
            query: User query
            user_id: User ID

        Returns:
            Response dict if a router confidently handles it, None otherwise
        """
        router = await cls._quick_filter_router(query, user_id)
        if router:
            return await router.handle(query, user_id)
        return None

    @classmethod
    def _error_response(cls, error_message: str) -> dict[str, Any]:
        """Generate error response.

        Args:
            error_message: Error description

        Returns:
            Error response dict
        """
        return {
            "content": "Có lỗi xảy ra khi xử lý câu hỏi.",
            "status": "error",
            "error": error_message,
            "citations": [],
            "sources": [],
            "metadata": {"router": "Registry", "agent": "error"},
            "latency_ms": 0,
            "retrieval_history": [],
        }

    @classmethod
    def list_routers(cls) -> list[str]:
        """List all registered router names.

        Returns:
            List of router names
        """
        return list(cls._routers.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered routers (mainly for testing)."""
        cls._routers.clear()
        cls._classifier = None


__all__ = ["RouterRegistry"]
