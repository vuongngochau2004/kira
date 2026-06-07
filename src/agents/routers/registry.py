"""Router registry for multi-stage query routing."""

import time
import logging
import re
import unicodedata
from uuid import UUID
from typing import Any, AsyncIterator, Optional

from src.agents.routers.base import BaseRouter
from src.agents.routers.classifier import (
    QueryClassifier,
    INTENT_TO_ROUTER,
)
from src.agents.routers.logging import routing_logger

logger = logging.getLogger(__name__)


class RouterRegistry:
    """Registry for managing and routing queries to appropriate routers.

    Multi-stage routing strategy:
    1. Quick Filter: Check all routers with can_handle() > QUICK_THRESHOLD
    2. Semantic Routing: Use embedding-based semantic similarity
    3. LLM Classification: If no semantic match, use LLM classifier
    4. Intent-based Routing: Map classified intent to router
    5. Fallback: Use default router if all else fails
    """

    QUICK_THRESHOLD = 0.7  # Confidence threshold for quick routing (lowered from 0.8 for better coverage - Phase 1.1 experiment)
    CLASSIFIER_THRESHOLD = 0.6  # Confidence threshold for LLM classification
    DEFAULT_ROUTER = "RAGRouter"

    _routers: dict[str, BaseRouter] = {}
    _classifier: QueryClassifier | None = None
    _semantic_router: Optional["KIRASemanticRouter"] = None

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
    def set_semantic_router(cls, semantic_router: "KIRASemanticRouter") -> None:
        """Set the semantic router instance.

        Args:
            semantic_router: KIRASemanticRouter instance
        """
        cls._semantic_router = semantic_router
        logger.info("Semantic router registered")

    @classmethod
    def get_semantic_router(cls) -> Optional["KIRASemanticRouter"]:
        """Get the semantic router instance.

        Returns:
            Semantic router instance or None
        """
        return cls._semantic_router

    @classmethod
    async def route(
        cls,
        query: str,
        user_id: str | UUID = "default",
        conversation_history: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Route query to appropriate router using multi-stage strategy.

        Args:
            query: User query
            user_id: User ID for filtering
            conversation_history: Optional conversation history for context

        Returns:
            Response dict from selected router
        """
        t0 = time.perf_counter()

        # Stage 1: Quick Filter - keyword-based confidence check
        quick_router = await cls._quick_filter_router(query, user_id)
        if quick_router is not None:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.debug(f"Quick routed to: {quick_router.get_name()}")

            # Log routing decision
            try:
                # Get confidence score for logging
                confidence = await quick_router.can_handle(query)
                routing_logger.log_quick_filter_decision(
                    query=query,
                    user_id=user_id,
                    router_selected=quick_router.get_name(),
                    confidence=confidence,
                    latency_ms=latency_ms,
                    conversation_history=conversation_history,
                )
            except Exception as e:
                logger.error(f"Failed to log routing decision: {e}")

            return await quick_router.handle(query, user_id, conversation_history=conversation_history)

        # Stage 2: Semantic Routing (NEW)
        if cls._semantic_router is not None:
            try:
                semantic_decision = await cls._semantic_router.route_async(query)

                if semantic_decision is not None:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    router_name = semantic_decision["router_name"]
                    router = cls._routers.get(router_name)

                    if router is not None:
                        logger.debug(
                            f"Semantic routed to: {router_name} "
                            f"(score: {semantic_decision['score']:.2f})"
                        )

                        # Log semantic routing decision
                        try:
                            routing_logger.log_semantic_decision(
                                query=query,
                                user_id=user_id,
                                router_selected=router_name,
                                semantic_route=semantic_decision["semantic_route"],
                                confidence=semantic_decision["score"],
                                latency_ms=latency_ms,
                                conversation_history=conversation_history,
                            )
                        except Exception as e:
                            logger.error(f"Failed to log semantic decision: {e}")

                        result = await router.handle(query, user_id, conversation_history=conversation_history)
                        result["latency_ms"] = latency_ms
                        result.setdefault("metadata", {})["routing_method"] = "semantic"
                        result.setdefault("metadata", {})["semantic_route"] = semantic_decision["semantic_route"]
                        result.setdefault("metadata", {})["semantic_score"] = semantic_decision["score"]
                        return result
            except Exception as e:
                logger.error(f"Semantic routing error: {e}")
                # Continue to LLM classification on error

        # Stage 3: LLM Classification
        if cls._classifier is None:
            cls._classifier = QueryClassifier()

        logger.debug("Using LLM classifier...")
        classification = await cls._classifier.classify(query)

        # Stage 4: Intent-based Routing
        router_name = INTENT_TO_ROUTER.get(
            classification.intent,
            cls.DEFAULT_ROUTER
        )

        router = cls._routers.get(router_name)
        if not router:
            logger.warning(f"Router not found: {router_name}, using default")
            router_name = cls.DEFAULT_ROUTER
            router = cls._routers.get(router_name)

        if not router:
            latency_ms = (time.perf_counter() - t0) * 1000
            routing_logger.log_fallback_decision(
                query=query,
                user_id=user_id,
                router_selected="None",
                latency_ms=latency_ms,
                conversation_history=conversation_history,
                reason="No routers available",
            )
            return cls._error_response("No routers available")

        # Check classification confidence
        if classification.confidence < cls.CLASSIFIER_THRESHOLD:
            logger.warning(
                f"Low confidence ({classification.confidence}): {classification.reason}"
            )

        # Stage 4: Execute Router
        try:
            result = await router.handle(query, user_id, conversation_history=conversation_history)
            latency_ms = (time.perf_counter() - t0) * 1000
            result["latency_ms"] = latency_ms
            result.setdefault("metadata", {})["classification"] = {
                "intent": classification.intent,
                "confidence": classification.confidence,
                "reason": classification.reason,
            }

            # Log routing decision
            try:
                routing_logger.log_llm_classification_decision(
                    query=query,
                    user_id=user_id,
                    router_selected=router.get_name(),
                    intent=classification.intent,
                    classification_confidence=classification.confidence,
                    latency_ms=latency_ms,
                    conversation_history=conversation_history,
                )
            except Exception as e:
                logger.error(f"Failed to log routing decision: {e}")

            return result
        except Exception as e:
            logger.error(f"Router {router_name} error: {e}")
            latency_ms = (time.perf_counter() - t0) * 1000
            routing_logger.log_fallback_decision(
                query=query,
                user_id=user_id,
                router_selected=router_name,
                latency_ms=latency_ms,
                conversation_history=conversation_history,
                reason=str(e),
            )
            return cls._error_response(str(e))

    @classmethod
    async def route_stream(
        cls,
        query: str,
        user_id: str | UUID = "default",
        conversation_history: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Route query to appropriate router with streaming response.

        Args:
            query: User query
            user_id: User ID for filtering
            conversation_history: Optional conversation history for context

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
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.debug(f"Quick routed to: {quick_router.get_name()}")

            # Log routing decision
            try:
                confidence = await quick_router.can_handle(query)
                routing_logger.log_quick_filter_decision(
                    query=query,
                    user_id=user_id,
                    router_selected=quick_router.get_name(),
                    confidence=confidence,
                    latency_ms=latency_ms,
                    conversation_history=conversation_history,
                )
            except Exception as e:
                logger.error(f"Failed to log routing decision: {e}")

            yield {
                "type": "routing",
                "data": {
                    "router": quick_router.get_name(),
                    "method": "quick_filter",
                },
            }
            async for chunk in quick_router.handle_stream(query, user_id, conversation_history=conversation_history):
                yield chunk
            return

        # Stage 2: Semantic Routing (NEW)
        if cls._semantic_router is not None:
            try:
                semantic_decision = await cls._semantic_router.route_async(query)

                if semantic_decision is not None:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    router_name = semantic_decision["router_name"]
                    router = cls._routers.get(router_name)

                    if router is not None:
                        logger.debug(
                            f"Semantic routed to: {router_name} "
                            f"(score: {semantic_decision['score']:.2f})"
                        )

                        # Log semantic routing decision
                        try:
                            routing_logger.log_semantic_decision(
                                query=query,
                                user_id=user_id,
                                router_selected=router_name,
                                semantic_route=semantic_decision["semantic_route"],
                                confidence=semantic_decision["score"],
                                latency_ms=latency_ms,
                                conversation_history=conversation_history,
                            )
                        except Exception as e:
                            logger.error(f"Failed to log semantic decision: {e}")

                        yield {
                            "type": "routing",
                            "data": {
                                "router": router_name,
                                "semantic_route": semantic_decision["semantic_route"],
                                "confidence": semantic_decision["score"],
                                "method": "semantic",
                            },
                        }

                        async for chunk in router.handle_stream(query, user_id, conversation_history=conversation_history):
                            yield chunk
                        return
            except Exception as e:
                logger.error(f"Semantic routing error: {e}")
                # Continue to LLM classification on error

        # Stage 3: LLM Classification
        if cls._classifier is None:
            cls._classifier = QueryClassifier()

        logger.debug("Using LLM classifier...")
        classification = await cls._classifier.classify(query)

        # Stage 4: Intent-based Routing
        router_name = INTENT_TO_ROUTER.get(
            classification.intent,
            cls.DEFAULT_ROUTER
        )

        router = cls._routers.get(router_name)
        if not router:
            logger.warning(f"Router not found: {router_name}, using default")
            router_name = cls.DEFAULT_ROUTER
            router = cls._routers.get(router_name)

        if not router:
            latency_ms = (time.perf_counter() - t0) * 1000
            routing_logger.log_fallback_decision(
                query=query,
                user_id=user_id,
                router_selected="None",
                latency_ms=latency_ms,
                conversation_history=conversation_history,
                reason="No routers available",
            )
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

        # Log routing decision
        try:
            routing_logger.log_llm_classification_decision(
                query=query,
                user_id=user_id,
                router_selected=router.get_name(),
                intent=classification.intent,
                classification_confidence=classification.confidence,
                latency_ms=0,  # Will be updated after completion
                conversation_history=conversation_history,
            )
        except Exception as e:
            logger.error(f"Failed to log routing decision: {e}")

        # Stage 4: Execute Router with streaming
        try:
            async for chunk in router.handle_stream(query, user_id, conversation_history=conversation_history):
                yield chunk

        except Exception as e:
            logger.error(f"Router {router_name} error: {e}")
            latency_ms = (time.perf_counter() - t0) * 1000
            routing_logger.log_fallback_decision(
                query=query,
                user_id=user_id,
                router_selected=router_name,
                latency_ms=latency_ms,
                conversation_history=conversation_history,
                reason=str(e),
            )
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": str(e),
                    "router": router.get_name(),
                },
            }

    @classmethod
    async def _try_fuzzy_match_filenames(
        cls,
        query: str,
        user_id: str | UUID = "default",
    ) -> BaseRouter | None:
        """Try fuzzy matching of filename stems against normalized query.

        Args:
            query: User query
            user_id: User ID

        Returns:
            RAGRouter if fuzzy match found, None otherwise
        """
        if not user_id or user_id == "default":
            return None

        try:
            from uuid import UUID as uuid_class
            from pathlib import Path

            # Convert user_id to UUID if needed
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid_class(user_id)
                except ValueError:
                    return None
            else:
                user_uuid = user_id

            if not user_uuid:
                return None

            from src.database.session import async_session_factory
            from src.indexing.document_store import list_documents

            async with async_session_factory() as session:
                docs, count = await list_documents(user_id=user_uuid, db=session)

                if count == 0:
                    return None

                # Fuzzy matching of filename stem against normalized query
                norm_query = cls._normalize_text(query)
                for doc in docs:
                    if doc.status != "deleted" and doc.filename:
                        stem = Path(doc.filename).stem
                        norm_stem = cls._normalize_text(stem)
                        if len(norm_stem) >= 3 and norm_stem in norm_query:
                            logger.debug(f"Fuzzy file match found: {doc.filename} in query")
                            return cls._routers.get("RAGRouter")

        except Exception as e:
            logger.error(f"Error in fuzzy filename matching: {e}", exc_info=True)

        return None

    @classmethod
    async def _try_file_keywords_match(
        cls,
        query: str,
        user_id: str | UUID = "default",
    ) -> BaseRouter | None:
        """Try matching file-related keywords in query.

        Args:
            query: User query
            user_id: User ID (to check if user has documents)

        Returns:
            RAGRouter if file keywords found and user has docs, None otherwise
        """
        if not user_id or user_id == "default":
            return None

        try:
            from uuid import UUID as uuid_class
            from src.database.session import async_session_factory
            from src.indexing.document_store import list_documents

            # Convert user_id to UUID if needed
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid_class(user_id)
                except ValueError:
                    return None
            else:
                user_uuid = user_id

            if not user_uuid:
                return None

            # Check if user has documents
            async with async_session_factory() as session:
                docs, count = await list_documents(user_id=user_uuid, db=session)

                if count == 0:
                    return None

            # Check for file keywords in query
            file_keywords = ["file", "tài liệu", "tập tin", "doc", "docx", "pdf", "txt", "đính kèm", "trích dẫn"]
            query_lower = query.lower()
            if any(kw in query_lower for kw in file_keywords):
                logger.debug("File keyword match with active user documents")
                return cls._routers.get("RAGRouter")

        except Exception as e:
            logger.error(f"Error in file keywords matching: {e}", exc_info=True)

        return None

    @classmethod
    async def _score_routers_confidence(cls, query: str) -> BaseRouter | None:
        """Score all routers by confidence and return best match.

        Args:
            query: User query

        Returns:
            Best matching router above threshold, or None
        """
        best_router: BaseRouter | None = None
        best_score = 0.0

        for router in cls._routers.values():
            score = await router.can_handle(query)
            if score > best_score and score >= cls.QUICK_THRESHOLD:
                best_score = score
                best_router = router

        return best_router

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
        """Quick filter stage - find router with high confidence using multiple strategies.

        Strategy order (try each until match):
        1. Fuzzy filename matching against user documents
        2. File keyword matching
        3. Confidence-based router scoring

        Args:
            query: User query
            user_id: User ID

        Returns:
            Best matching router or None
        """
        # Strategy 1: Try fuzzy filename matching
        if router := await cls._try_fuzzy_match_filenames(query, user_id):
            return router

        # Strategy 2: Try file keyword matching
        if router := await cls._try_file_keywords_match(query, user_id):
            return router

        # Strategy 3: Fall back to confidence-based scoring
        return await cls._score_routers_confidence(query)

    @classmethod
    async def _quick_filter(
        cls,
        query: str,
        user_id: str | UUID,
        conversation_history: list[dict] | None = None,
    ) -> dict[str, Any] | None:
        """Quick filter stage - check routers with high confidence.

        Args:
            query: User query
            user_id: User ID
            conversation_history: Optional conversation history for context

        Returns:
            Response dict if a router confidently handles it, None otherwise
        """
        router = await cls._quick_filter_router(query, user_id)
        if router:
            return await router.handle(query, user_id, conversation_history=conversation_history)
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
