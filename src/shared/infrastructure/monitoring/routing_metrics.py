"""Routing metrics collection and analysis for monitoring.

This module provides:
- Metrics aggregation from routing logs
- Performance analysis
- Routing accuracy tracking
- Cost optimization insights

Usage:
    from src.shared.infrastructure.monitoring.routing_metrics import RoutingMetricsCollector

    collector = RoutingMetricsCollector()
    metrics = collector.get_metrics_summary()
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
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
    """Aggregated metrics for routing performance."""

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
    """Collector for routing metrics from logs."""

    def __init__(self):
        """Initialize metrics collector."""
        self._decisions: list[dict] = []
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._confidences: dict[str, list[float]] = defaultdict(list)

    def add_decision(self, decision: dict) -> None:
        """Add a routing decision for metrics collection."""
        self._decisions.append(decision)
        method = decision.get("method", "unknown")
        latency = decision.get("latency_ms", 0)
        self._latencies[method].append(latency)
        router = decision.get("router", "unknown")
        confidence = decision.get("confidence", 0)
        self._confidences[router].append(confidence)

    def get_metrics_summary(self, time_window_seconds: int = 3600) -> RoutingMetrics:
        """Get aggregated metrics summary."""
        if not self._decisions:
            return RoutingMetrics()

        now = time.time()
        cutoff = now - time_window_seconds
        recent_decisions = [
            d for d in self._decisions
            if d.get("timestamp", 0) > cutoff
        ]

        if not recent_decisions:
            return RoutingMetrics()

        metrics = RoutingMetrics()
        metrics.total_requests = len(recent_decisions)

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

        if metrics.total_requests > 0:
            metrics.context_usage = context_count / metrics.total_requests
            metrics.llm_classification_rate = llm_count / metrics.total_requests
            metrics.quick_filter_coverage = quick_count / metrics.total_requests

        for method, latencies in self._latencies.items():
            if latencies:
                recent_latencies = [l for l in latencies if l > 0]
                if recent_latencies:
                    metrics.avg_latency_ms[method] = sum(recent_latencies) / len(recent_latencies)
                    sorted_latencies = sorted(recent_latencies)
                    p95_idx = int(len(sorted_latencies) * 0.95)
                    if p95_idx < len(sorted_latencies):
                        metrics.p95_latency_ms[method] = sorted_latencies[p95_idx]

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
        """Get queries with low confidence scores."""
        problematic = [
            d for d in self._decisions
            if d.get("confidence", 1.0) < min_confidence
        ]
        problematic.sort(key=lambda x: x.get("confidence", 0))
        return problematic[:limit]

    def get_hourly_distribution(self, hours: int = 24) -> dict[str, dict]:
        """Get routing method distribution by hour."""
        now = time.time()
        hourly_data: dict[str, dict] = {}

        for i in range(hours):
            hour_start = now - (i + 1) * 3600
            hour_end = now - i * 3600
            hour_key = datetime.fromtimestamp(hour_start).strftime("%Y-%m-%d %H:00")

            hour_decisions = [
                d for d in self._decisions
                if hour_start <= d.get("timestamp", 0) < hour_end
            ]

            method_counts = defaultdict(int)
            for decision in hour_decisions:
                method = decision.get("method", "unknown")
                method_counts[method] += 1

            hourly_data[hour_key] = dict(method_counts)

        return hourly_data

    def analyze_baseline(self) -> dict[str, Any]:
        """Analyze baseline metrics for Go/No-Go decision."""
        metrics = self.get_metrics_summary()

        analysis = {
            "metrics": metrics.to_dict(),
            "analysis": {},
            "recommendations": [],
        }

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

        avg_latency = metrics.avg_latency_ms.get(RoutingMethod.LLM_CLASSIFICATION.value, 0)
        analysis["avg_llm_latency_ms"] = avg_latency

        if avg_latency > 500:
            analysis["analysis"]["latency"] = "HIGH - Performance concern"
            analysis["recommendations"].append("GO: Average LLM latency > 500ms indicates performance issue")
        else:
            analysis["analysis"]["latency"] = "ACCEPTABLE"
            analysis["recommendations"].append("Latency within acceptable range")

        quick_coverage = metrics.quick_filter_coverage
        analysis["quick_filter_coverage"] = quick_coverage

        if quick_coverage < 0.2:
            analysis["analysis"]["quick_filter"] = "LOW - Room for improvement"
            analysis["recommendations"].append("GO: Quick filter coverage < 20%, significant improvement possible")
        elif quick_coverage > 0.5:
            analysis["analysis"]["quick_filter"] = "HIGH - Already effective"
            analysis["recommendations"].append("NO-GO: Quick filter coverage > 50%, already performing well")

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
        """Clear old decision data beyond retention period."""
        now = time.time()
        cutoff = now - retention_seconds

        original_count = len(self._decisions)
        self._decisions = [d for d in self._decisions if d.get("timestamp", 0) > cutoff]

        return original_count - len(self._decisions)


# Global metrics collector instance
_routing_metrics_collector: Optional[RoutingMetricsCollector] = None


def get_metrics_collector() -> RoutingMetricsCollector:
    """Get the global metrics collector instance."""
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