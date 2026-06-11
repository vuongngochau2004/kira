"""Routing metrics collection and analysis for monitoring.

This module provides:
- Metrics aggregation from routing logs
- Performance analysis
- Routing accuracy tracking
- Cost optimization insights

Usage:
    from monitoring.routing_metrics import RoutingMetricsCollector

    collector = RoutingMetricsCollector()
    metrics = collector.get_metrics_summary()
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class RoutingMethod(Enum):
    """Routing method types."""
    QUICK_FILTER = "quick_filter"
    LLM_CLASSIFICATION = "llm_classification"
    FALLBACK = "fallback"


@dataclass
class RoutingMetrics:
    """Aggregated metrics for routing performance.

    Attributes:
        total_requests: Total number of routing requests
        method_distribution: Count of requests per routing method
        avg_latency_ms: Average latency per routing method
        p95_latency_ms: 95th percentile latency per method
        confidence_distribution: Average confidence scores per router
        accuracy_metrics: Routing accuracy measurements
        cost_metrics: LLM classification cost tracking
        context_usage: Percentage of requests with conversation context
    """

    total_requests: int = 0
    method_distribution: dict[str, int] = field(default_factory=dict)
    avg_latency_ms: dict[str, float] = field(default_factory=dict)
    p95_latency_ms: dict[str, float] = field(default_factory=dict)
    confidence_distribution: dict[str, float] = field(default_factory=dict)
    router_distribution: dict[str, int] = field(default_factory=dict)
    context_usage: float = 0.0
    llm_classification_rate: float = 0.0
    quick_filter_coverage: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_requests": self.total_requests,
            "method_distribution": self.method_distribution,
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "confidence_distribution": self.confidence_distribution,
            "router_distribution": self.router_distribution,
            "context_usage_percentage": self.context_usage * 100,
            "llm_classification_rate": self.llm_classification_rate * 100,
            "quick_filter_coverage": self.quick_filter_coverage * 100,
        }


class RoutingMetricsCollector:
    """Collector for routing metrics from logs.

    This class aggregates routing decision data from logs
    and provides summary metrics for analysis.

    In production, this would connect to a log aggregation system
    (ELK, Loki, etc.) or database to query routing decisions.

    For now, it provides in-memory aggregation for testing and development.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._decisions: list[dict] = []
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._confidences: dict[str, list[float]] = defaultdict(list)

    def add_decision(self, decision: dict) -> None:
        """Add a routing decision for metrics collection.

        Args:
            decision: Routing decision dictionary (from RoutingDecision.to_log_dict())
        """
        self._decisions.append(decision)

        # Track latencies
        method = decision.get("method", "unknown")
        latency = decision.get("latency_ms", 0)
        self._latencies[method].append(latency)

        # Track confidences
        router = decision.get("router", "unknown")
        confidence = decision.get("confidence", 0)
        self._confidences[router].append(confidence)

    def get_metrics_summary(self, time_window_seconds: int = 3600) -> RoutingMetrics:
        """Get aggregated metrics summary.

        Args:
            time_window_seconds: Time window for metrics (default 1 hour)

        Returns:
            RoutingMetrics with aggregated data
        """
        if not self._decisions:
            return RoutingMetrics()

        now = time.time()
        cutoff = now - time_window_seconds

        # Filter decisions within time window
        recent_decisions = [
            d for d in self._decisions
            if d.get("timestamp", 0) > cutoff
        ]

        if not recent_decisions:
            return RoutingMetrics()

        metrics = RoutingMetrics()

        # Total requests
        metrics.total_requests = len(recent_decisions)

        # Method distribution
        method_counts = defaultdict(int)
        context_count = 0
        llm_count = 0
        quick_count = 0

        for decision in recent_decisions:
            method = decision.get("method", "unknown")
            method_counts[method] += 1

            if decision.get("has_context"):
                context_count += 1

            if method == RoutingMethod.LLM_CLASSIFICATION.value:
                llm_count += 1
            elif method == RoutingMethod.QUICK_FILTER.value:
                quick_count += 1

        metrics.method_distribution = dict(method_counts)

        # Calculate percentages
        if metrics.total_requests > 0:
            metrics.context_usage = context_count / metrics.total_requests
            metrics.llm_classification_rate = llm_count / metrics.total_requests
            metrics.quick_filter_coverage = quick_count / metrics.total_requests

        # Average latencies
        for method, latencies in self._latencies.items():
            if latencies:
                recent_latencies = [
                    l for l in latencies
                    if l > 0  # Filter out zero latencies (streaming)
                ]
                if recent_latencies:
                    metrics.avg_latency_ms[method] = sum(recent_latencies) / len(recent_latencies)

                    # Calculate P95
                    sorted_latencies = sorted(recent_latencies)
                    p95_idx = int(len(sorted_latencies) * 0.95)
                    if p95_idx < len(sorted_latencies):
                        metrics.p95_latency_ms[method] = sorted_latencies[p95_idx]

        # Confidence distribution by router
        router_counts = defaultdict(int)
        router_confidences = defaultdict(list)

        for decision in recent_decisions:
            router = decision.get("router", "unknown")
            router_counts[router] += 1

            confidence = decision.get("confidence", 0)
            if confidence > 0:
                router_confidences[router].append(confidence)

        metrics.router_distribution = dict(router_counts)

        for router, confidences in router_confidences.items():
            if confidences:
                metrics.confidence_distribution[router] = sum(confidences) / len(confidences)

        return metrics

    def get_problematic_queries(
        self,
        min_confidence: float = 0.6,
        limit: int = 10,
    ) -> list[dict]:
        """Get queries with low confidence scores.

        Args:
            min_confidence: Minimum confidence threshold
            limit: Maximum number of queries to return

        Returns:
            List of problematic query details
        """
        problematic = [
            d for d in self._decisions
            if d.get("confidence", 1.0) < min_confidence
        ]

        # Sort by confidence (lowest first)
        problematic.sort(key=lambda x: x.get("confidence", 0))

        return problematic[:limit]

    def get_hourly_distribution(self, hours: int = 24) -> dict[str, dict]:
        """Get routing method distribution by hour.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary with hourly breakdown of routing methods
        """
        now = time.time()
        hourly_data: dict[str, dict] = {}

        for i in range(hours):
            hour_start = now - (i + 1) * 3600
            hour_end = now - i * 3600
            hour_key = datetime.fromtimestamp(hour_start).strftime("%Y-%m-%d %H:00")

            # Filter decisions for this hour
            hour_decisions = [
                d for d in self._decisions
                if hour_start <= d.get("timestamp", 0) < hour_end
            ]

            # Count methods
            method_counts = defaultdict(int)
            for decision in hour_decisions:
                method = decision.get("method", "unknown")
                method_counts[method] += 1

            hourly_data[hour_key] = dict(method_counts)

        return hourly_data

    def analyze_baseline(self) -> dict[str, Any]:
        """Analyze baseline metrics for Go/No-Go decision.

        Returns:
            Dictionary with baseline analysis and recommendations
        """
        metrics = self.get_metrics_summary()

        analysis = {
            "metrics": metrics.to_dict(),
            "analysis": {},
            "recommendations": [],
        }

        # Analyze LLM classification rate
        llm_rate = metrics.llm_classification_rate
        analysis["llm_classification_rate"] = llm_rate

        if llm_rate > 0.5:
            analysis["analysis"]["llm_classification"] = "HIGH - Problem validated"
            analysis["recommendations"].append("GO: LLM classification rate > 50% justifies optimization")
        elif llm_rate < 0.3:
            analysis["analysis"]["llm_classification"] = "LOW - Problem may be overstated"
            analysis["recommendations"].append("NO-GO: LLM classification rate < 30%, minimal optimization needed")
        else:
            analysis["analysis"]["llm_classification"] = "MEDIUM - Marginal case"
            analysis["recommendations"].append("EVALUATE: LLM classification rate 30-50%, assess other factors")

        # Analyze latency
        avg_latency = metrics.avg_latency_ms.get(RoutingMethod.LLM_CLASSIFICATION.value, 0)
        analysis["avg_llm_latency_ms"] = avg_latency

        if avg_latency > 500:
            analysis["analysis"]["latency"] = "HIGH - Performance concern"
            analysis["recommendations"].append("GO: Average LLM latency > 500ms indicates performance issue")
        else:
            analysis["analysis"]["latency"] = "ACCEPTABLE"
            analysis["recommendations"].append("Latency within acceptable range")

        # Analyze quick filter coverage
        quick_coverage = metrics.quick_filter_coverage
        analysis["quick_filter_coverage"] = quick_coverage

        if quick_coverage < 0.2:
            analysis["analysis"]["quick_filter"] = "LOW - Room for improvement"
            analysis["recommendations"].append("GO: Quick filter coverage < 20%, significant improvement possible")
        elif quick_coverage > 0.5:
            analysis["analysis"]["quick_filter"] = "HIGH - Already effective"
            analysis["recommendations"].append("NO-GO: Quick filter coverage > 50%, already performing well")

        # Overall recommendation
        go_votes = sum(1 for rec in analysis["recommendations"] if rec.startswith("GO"))
        no_go_votes = sum(1 for rec in analysis["recommendations"] if rec.startswith("NO-GO"))

        if go_votes >= 2:
            analysis["overall_recommendation"] = "GO - Proceed with Phase 1"
        elif no_go_votes >= 2:
            analysis["overall_recommendation"] = "NO-GO - Problem not significant enough"
        else:
            analysis["overall_recommendation"] = "EVALUATE - Mixed signals, assess business priorities"

        return analysis

    def clear_old_data(self, retention_seconds: int = 86400) -> int:
        """Clear old decision data beyond retention period.

        Args:
            retention_seconds: Data retention period (default 24 hours)

        Returns:
            Number of decisions cleared
        """
        now = time.time()
        cutoff = now - retention_seconds

        original_count = len(self._decisions)
        self._decisions = [d for d in self._decisions if d.get("timestamp", 0) > cutoff]

        return original_count - len(self._decisions)


# Global metrics collector instance
_routing_metrics_collector: Optional[RoutingMetricsCollector] = None


def get_metrics_collector() -> RoutingMetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        RoutingMetricsCollector instance
    """
    global _routing_metrics_collector
    if _routing_metrics_collector is None:
        _routing_metrics_collector = RoutingMetricsCollector()
    return _routing_metrics_collector


__all__ = [
    "RoutingMethod",
    "RoutingMetrics",
    "RoutingMetricsCollector",
    "get_metrics_collector",
]
