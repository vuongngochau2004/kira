"""DEPRECATED: Use src.shared.infrastructure.monitoring.routing_metrics instead."""

from src.shared.infrastructure.monitoring.routing_metrics import (
    RoutingMethod,
    RoutingMetrics,
    RoutingMetricsCollector,
    get_metrics_collector,
)

__all__ = [
    "RoutingMethod",
    "RoutingMetrics",
    "RoutingMetricsCollector",
    "get_metrics_collector",
]
