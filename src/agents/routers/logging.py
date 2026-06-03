"""Routing decision logging for metrics collection and analysis.

This module provides structured logging for routing decisions to enable:
- Baseline metrics collection
- Performance analysis
- Routing accuracy tracking
- Cost optimization insights
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID


logger = logging.getLogger("routing.metrics")


@dataclass
class RoutingDecision:
    """Structured data for a routing decision.

    Attributes:
        timestamp: Unix timestamp when decision was made
        user_id: User identifier (hashed for privacy)
        query: Original user query
        query_hash: SHA256 hash of query (for privacy-safe aggregation)
        router_selected: Name of the router that handled the query
        confidence: Confidence score for routing decision (0.0-1.0)
        method: Routing method used ("quick_filter", "llm_classification", "fallback")
        latency_ms: Total routing latency in milliseconds
        has_conversation_context: Whether conversation history was provided
        conversation_length: Number of messages in conversation history
        intent: Classified intent (if LLM classification was used)
        classification_confidence: Confidence from LLM classifier (if applicable)
    """

    timestamp: float
    user_id: str
    query: str
    query_hash: str
    router_selected: str
    confidence: float
    method: str
    latency_ms: float
    has_conversation_context: bool
    conversation_length: int
    intent: str | None = None
    classification_confidence: float | None = None

    def to_log_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for JSON logging.

        Returns:
            Dictionary with routing decision data
        """
        return {
            "event": "routing_decision",
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "query_hash": self.query_hash,
            "router": self.router_selected,
            "confidence": self.confidence,
            "method": self.method,
            "latency_ms": self.latency_ms,
            "has_context": self.has_conversation_context,
            "conv_length": self.conversation_length,
            "intent": self.intent,
            "classification_confidence": self.classification_confidence,
        }

    def to_json(self) -> str:
        """Convert to JSON string.

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_log_dict())


class RoutingLogger:
    """Logger for routing decisions with structured output.

    This logger outputs routing decisions in structured JSON format
    for easy parsing by log aggregation systems and metrics dashboards.

    Usage:
        logger = RoutingLogger()
        logger.log_decision(RoutingDecision(...))
    """

    def __init__(self, enabled: bool = True):
        """Initialize routing logger.

        Args:
            enabled: Whether logging is enabled (can be disabled via env var)
        """
        self.enabled = enabled
        self.logger = logging.getLogger("routing.metrics")

    @staticmethod
    def hash_query(query: str, length: int = 16) -> str:
        """Generate hash of query for privacy-safe tracking.

        Args:
            query: User query string
            length: Length of hash to return (default 16)

        Returns:
            Hex digest of SHA256 hash (truncated)
        """
        return hashlib.sha256(query.encode("utf-8")).hexdigest()[:length]

    @staticmethod
    def normalize_user_id(user_id: str | UUID) -> str:
        """Normalize user ID for logging.

        Args:
            user_id: User ID (string or UUID)

        Returns:
            String representation of user ID
        """
        if isinstance(user_id, UUID):
            return str(user_id)
        return user_id

    def log_decision(self, decision: RoutingDecision) -> None:
        """Log a routing decision.

        Args:
            decision: RoutingDecision to log
        """
        if not self.enabled:
            return

        try:
            self.logger.info(decision.to_json())

            # Also add to metrics collector
            try:
                from src.monitoring.routing_metrics import get_metrics_collector
                collector = get_metrics_collector()
                collector.add_decision(decision.to_log_dict())
            except Exception as metrics_error:
                # Don't let metrics errors break routing
                self.logger.debug(f"Failed to add to metrics collector: {metrics_error}")

        except Exception as e:
            # Don't let logging errors break routing
            self.logger.error(f"Failed to log routing decision: {e}")

    def log_quick_filter_decision(
        self,
        query: str,
        user_id: str | UUID,
        router_selected: str,
        confidence: float,
        latency_ms: float,
        conversation_history: list[dict] | None = None,
    ) -> None:
        """Log a quick filter routing decision.

        Args:
            query: User query
            user_id: User ID
            router_selected: Router that was selected
            confidence: Confidence score
            latency_ms: Routing latency
            conversation_history: Optional conversation history
        """
        decision = RoutingDecision(
            timestamp=time.time(),
            user_id=self.normalize_user_id(user_id),
            query=query,
            query_hash=self.hash_query(query),
            router_selected=router_selected,
            confidence=confidence,
            method="quick_filter",
            latency_ms=latency_ms,
            has_conversation_context=conversation_history is not None,
            conversation_length=len(conversation_history) if conversation_history else 0,
        )
        self.log_decision(decision)

    def log_llm_classification_decision(
        self,
        query: str,
        user_id: str | UUID,
        router_selected: str,
        intent: str,
        classification_confidence: float,
        latency_ms: float,
        conversation_history: list[dict] | None = None,
    ) -> None:
        """Log an LLM classification routing decision.

        Args:
            query: User query
            user_id: User ID
            router_selected: Router that was selected
            intent: Classified intent
            classification_confidence: Confidence from classifier
            latency_ms: Routing latency
            conversation_history: Optional conversation history
        """
        decision = RoutingDecision(
            timestamp=time.time(),
            user_id=self.normalize_user_id(user_id),
            query=query,
            query_hash=self.hash_query(query),
            router_selected=router_selected,
            confidence=classification_confidence,
            method="llm_classification",
            latency_ms=latency_ms,
            has_conversation_context=conversation_history is not None,
            conversation_length=len(conversation_history) if conversation_history else 0,
            intent=intent,
            classification_confidence=classification_confidence,
        )
        self.log_decision(decision)

    def log_fallback_decision(
        self,
        query: str,
        user_id: str | UUID,
        router_selected: str,
        latency_ms: float,
        conversation_history: list[dict] | None = None,
        reason: str | None = None,
    ) -> None:
        """Log a fallback routing decision.

        Args:
            query: User query
            user_id: User ID
            router_selected: Default router that was used
            latency_ms: Routing latency
            conversation_history: Optional conversation history
            reason: Optional reason for fallback
        """
        decision = RoutingDecision(
            timestamp=time.time(),
            user_id=self.normalize_user_id(user_id),
            query=query,
            query_hash=self.hash_query(query),
            router_selected=router_selected,
            confidence=0.0,
            method="fallback",
            latency_ms=latency_ms,
            has_conversation_context=conversation_history is not None,
            conversation_length=len(conversation_history) if conversation_history else 0,
        )
        self.log_decision(decision)
        if reason:
            self.logger.warning(f"Fallback routing: {reason}")

    def log_semantic_decision(
        self,
        query: str,
        user_id: str | UUID,
        router_selected: str,
        semantic_route: str,
        confidence: float,
        latency_ms: float,
        conversation_history: list[dict] | None = None,
    ) -> None:
        """Log a semantic routing decision.

        Args:
            query: User query
            user_id: User ID
            router_selected: Router that was selected
            semantic_route: Semantic route name
            confidence: Confidence score from semantic router
            latency_ms: Routing latency
            conversation_history: Optional conversation history
        """
        decision = RoutingDecision(
            timestamp=time.time(),
            user_id=self.normalize_user_id(user_id),
            query=query,
            query_hash=self.hash_query(query),
            router_selected=router_selected,
            confidence=confidence,
            method="semantic",
            latency_ms=latency_ms,
            has_conversation_context=conversation_history is not None,
            conversation_length=len(conversation_history) if conversation_history else 0,
            intent=semantic_route,  # Store semantic route as intent
        )
        self.log_decision(decision)


# Global logger instance
routing_logger = RoutingLogger(
    enabled=True  # Can be controlled via environment variable in future
)


__all__ = [
    "RoutingDecision",
    "RoutingLogger",
    "routing_logger",
]
