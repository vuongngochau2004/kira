"""Dashboard configuration for Agentic RAG monitoring.

This module provides:
- Dashboard metric definitions
- Alerting thresholds
- Trend analysis configuration
- Comparison views (before/after)

Usage:
    from src.shared.infrastructure.monitoring.dashboard_config import DashboardConfig

    config = DashboardConfig()
    metrics = config.get_key_metrics()
    alerts = config.check_alerts(current_metrics)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of dashboard metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TREND = "trend"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricDefinition:
    """Definition of a dashboard metric."""

    name: str
    type: MetricType
    description: str
    unit: str
    category: str
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "unit": self.unit,
            "category": self.category,
            "threshold_warning": self.threshold_warning,
            "threshold_critical": self.threshold_critical,
            "enabled": self.enabled,
        }


@dataclass
class AlertRule:
    """Alert rule definition."""

    rule_id: str
    metric_name: str
    condition: str
    threshold: float
    severity: AlertSeverity
    message: str
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "metric_name": self.metric_name,
            "condition": self.condition,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "message": self.message,
            "enabled": self.enabled,
        }

    def check(self, value: float) -> Optional[dict[str, Any]]:
        """Check if alert should trigger."""
        if not self.enabled:
            return None

        triggered = False
        if self.condition == "gt" and value > self.threshold:
            triggered = True
        elif self.condition == "lt" and value < self.threshold:
            triggered = True
        elif self.condition == "eq" and value == self.threshold:
            triggered = True

        if triggered:
            return {
                "rule_id": self.rule_id,
                "metric_name": self.metric_name,
                "severity": self.severity.value,
                "message": self.message.format(value=value, threshold=self.threshold),
                "current_value": value,
                "threshold": self.threshold,
                "timestamp": datetime.utcnow().isoformat(),
            }

        return None


@dataclass
class DashboardConfig:
    """Dashboard configuration for Agentic RAG monitoring."""

    metrics: dict[str, MetricDefinition] = field(default_factory=dict)
    alert_rules: dict[str, AlertRule] = field(default_factory=dict)
    trend_windows: dict[str, int] = field(default_factory=dict)

    def __init__(self):
        """Initialize dashboard configuration with defaults."""
        self._init_default_metrics()
        self._init_default_alerts()
        self._init_trend_windows()

    def _init_default_metrics(self) -> None:
        """Initialize default metric definitions."""
        self.metrics["faithfulness"] = MetricDefinition(
            name="faithfulness",
            type=MetricType.GAUGE,
            description="Answer groundedness in retrieved contexts",
            unit="score",
            category="quality",
            threshold_warning=0.7,
            threshold_critical=0.5,
        )

        self.metrics["answer_relevancy"] = MetricDefinition(
            name="answer_relevancy",
            type=MetricType.GAUGE,
            description="Relevance of answer to query",
            unit="score",
            category="quality",
            threshold_warning=0.7,
            threshold_critical=0.5,
        )

        self.metrics["context_precision"] = MetricDefinition(
            name="context_precision",
            type=MetricType.GAUGE,
            description="Precision of retrieved contexts",
            unit="score",
            category="quality",
            threshold_warning=0.7,
            threshold_critical=0.5,
        )

        self.metrics["context_recall"] = MetricDefinition(
            name="context_recall",
            type=MetricType.GAUGE,
            description="Recall of relevant contexts",
            unit="score",
            category="quality",
            threshold_warning=0.7,
            threshold_critical=0.5,
        )

        self.metrics["avg_latency_ms"] = MetricDefinition(
            name="avg_latency_ms",
            type=MetricType.GAUGE,
            description="Average query latency",
            unit="ms",
            category="performance",
            threshold_warning=3000,
            threshold_critical=5000,
        )

        self.metrics["p95_latency_ms"] = MetricDefinition(
            name="p95_latency_ms",
            type=MetricType.GAUGE,
            description="95th percentile latency",
            unit="ms",
            category="performance",
            threshold_warning=5000,
            threshold_critical=10000,
        )

        self.metrics["throughput_qps"] = MetricDefinition(
            name="throughput_qps",
            type=MetricType.GAUGE,
            description="Queries per second",
            unit="qps",
            category="performance",
            threshold_warning=1.0,
            threshold_critical=0.5,
        )

        self.metrics["agent_success_rate"] = MetricDefinition(
            name="agent_success_rate",
            type=MetricType.GAUGE,
            description="Agent call success rate",
            unit="rate",
            category="agent",
            threshold_warning=0.95,
            threshold_critical=0.9,
        )

        self.metrics["graph_retry_rate"] = MetricDefinition(
            name="graph_retry_rate",
            type=MetricType.GAUGE,
            description="Graph execution retry rate",
            unit="rate",
            category="agent",
            threshold_warning=0.1,
            threshold_critical=0.2,
        )

        self.metrics["graph_avg_iterations"] = MetricDefinition(
            name="graph_avg_iterations",
            type=MetricType.GAUGE,
            description="Average graph iterations per query",
            unit="iterations",
            category="agent",
            threshold_warning=3.0,
            threshold_critical=5.0,
        )

        self.metrics["user_satisfaction_rate"] = MetricDefinition(
            name="user_satisfaction_rate",
            type=MetricType.GAUGE,
            description="User satisfaction rate (thumbs up / total)",
            unit="rate",
            category="user",
            threshold_warning=0.8,
            threshold_critical=0.7,
        )

        self.metrics["user_avg_rating"] = MetricDefinition(
            name="user_avg_rating",
            type=MetricType.GAUGE,
            description="Average user rating (1-5)",
            unit="rating",
            category="user",
            threshold_warning=4.0,
            threshold_critical=3.5,
        )

        self.metrics["cost_per_query_usd"] = MetricDefinition(
            name="cost_per_query_usd",
            type=MetricType.GAUGE,
            description="Average cost per query",
            unit="usd",
            category="cost",
            threshold_warning=0.01,
            threshold_critical=0.02,
        )

        self.metrics["total_daily_cost_usd"] = MetricDefinition(
            name="total_daily_cost_usd",
            type=MetricType.COUNTER,
            description="Total daily cost",
            unit="usd",
            category="cost",
            threshold_warning=100.0,
            threshold_critical=200.0,
        )

        self.metrics["tokens_per_query"] = MetricDefinition(
            name="tokens_per_query",
            type=MetricType.GAUGE,
            description="Average tokens per query",
            unit="tokens",
            category="cost",
            threshold_warning=5000,
            threshold_critical=10000,
        )

    def _init_default_alerts(self) -> None:
        """Initialize default alert rules."""
        self.alert_rules["faithfulness_low"] = AlertRule(
            rule_id="faithfulness_low",
            metric_name="faithfulness",
            condition="lt",
            threshold=0.7,
            severity=AlertSeverity.WARNING,
            message="Faithfulness dropped to {value:.2f} (threshold: {threshold:.2f})",
        )

        self.alert_rules["faithfulness_critical"] = AlertRule(
            rule_id="faithfulness_critical",
            metric_name="faithfulness",
            condition="lt",
            threshold=0.5,
            severity=AlertSeverity.CRITICAL,
            message="CRITICAL: Faithfulness dropped to {value:.2f} (threshold: {threshold:.2f})",
        )

        self.alert_rules["answer_relevancy_low"] = AlertRule(
            rule_id="answer_relevancy_low",
            metric_name="answer_relevancy",
            condition="lt",
            threshold=0.7,
            severity=AlertSeverity.WARNING,
            message="Answer relevancy dropped to {value:.2f} (threshold: {threshold:.2f})",
        )

        self.alert_rules["latency_high"] = AlertRule(
            rule_id="latency_high",
            metric_name="avg_latency_ms",
            condition="gt",
            threshold=3000,
            severity=AlertSeverity.WARNING,
            message="Latency increased to {value:.0f}ms (threshold: {threshold:.0f}ms)",
        )

        self.alert_rules["latency_critical"] = AlertRule(
            rule_id="latency_critical",
            metric_name="avg_latency_ms",
            condition="gt",
            threshold=5000,
            severity=AlertSeverity.CRITICAL,
            message="CRITICAL: Latency increased to {value:.0f}ms (threshold: {threshold:.0f}ms)",
        )

        self.alert_rules["agent_failure_rate"] = AlertRule(
            rule_id="agent_failure_rate",
            metric_name="agent_success_rate",
            condition="lt",
            threshold=0.95,
            severity=AlertSeverity.WARNING,
            message="Agent success rate dropped to {value:.2%} (threshold: {threshold:.2%})",
        )

        self.alert_rules["graph_retry_high"] = AlertRule(
            rule_id="graph_retry_high",
            metric_name="graph_retry_rate",
            condition="gt",
            threshold=0.1,
            severity=AlertSeverity.WARNING,
            message="Graph retry rate increased to {value:.2%} (threshold: {threshold:.2%})",
        )

        self.alert_rules["cost_high"] = AlertRule(
            rule_id="cost_high",
            metric_name="cost_per_query_usd",
            condition="gt",
            threshold=0.01,
            severity=AlertSeverity.WARNING,
            message="Cost per query increased to ${value:.4f} (threshold: ${threshold:.4f})",
        )

        self.alert_rules["satisfaction_low"] = AlertRule(
            rule_id="satisfaction_low",
            metric_name="user_satisfaction_rate",
            condition="lt",
            threshold=0.8,
            severity=AlertSeverity.WARNING,
            message="User satisfaction dropped to {value:.2%} (threshold: {threshold:.2%})",
        )

    def _init_trend_windows(self) -> None:
        """Initialize trend analysis windows."""
        self.trend_windows = {
            "short": 1,
            "medium": 6,
            "long": 24,
        }

    def get_metric_definition(self, metric_name: str) -> Optional[MetricDefinition]:
        """Get metric definition by name."""
        return self.metrics.get(metric_name)

    def get_key_metrics(self) -> dict[str, MetricDefinition]:
        """Get key metrics for dashboard."""
        key_metric_names = [
            "faithfulness",
            "answer_relevancy",
            "avg_latency_ms",
            "agent_success_rate",
            "user_satisfaction_rate",
            "cost_per_query_usd",
            "context_precision",
            "graph_retry_rate",
            "throughput_qps",
            "user_avg_rating",
        ]

        return {name: self.metrics[name] for name in key_metric_names if name in self.metrics}

    def get_metrics_by_category(self, category: str) -> dict[str, MetricDefinition]:
        """Get metrics by category."""
        return {
            name: metric
            for name, metric in self.metrics.items()
            if metric.category == category and metric.enabled
        }

    def check_alerts(self, current_metrics: dict[str, float]) -> list[dict[str, Any]]:
        """Check all alert rules against current metrics."""
        triggered_alerts = []

        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue

            metric_value = current_metrics.get(rule.metric_name)
            if metric_value is None:
                continue

            alert = rule.check(metric_value)
            if alert:
                triggered_alerts.append(alert)

        severity_order = {"critical": 0, "warning": 1, "info": 2}
        triggered_alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))

        return triggered_alerts

    def get_trend_config(self, window: str = "medium") -> dict[str, Any]:
        """Get trend analysis configuration."""
        hours = self.trend_windows.get(window, 6)

        return {
            "window": window,
            "hours": hours,
            "interval_minutes": 5,
            "min_data_points": 6,
        }

    def export_config(self, filepath: str) -> None:
        """Export configuration to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metrics": {name: m.to_dict() for name, m in self.metrics.items()},
            "alert_rules": {rule_id: r.to_dict() for rule_id, r in self.alert_rules.items()},
            "trend_windows": self.trend_windows,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported dashboard config to {filepath}")

    @classmethod
    def load_config(cls, filepath: str) -> "DashboardConfig":
        """Load configuration from JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = cls()

        for name, metric_data in data.get("metrics", {}).items():
            config.metrics[name] = MetricDefinition(
                name=metric_data["name"],
                type=MetricType(metric_data["type"]),
                description=metric_data["description"],
                unit=metric_data["unit"],
                category=metric_data["category"],
                threshold_warning=metric_data.get("threshold_warning"),
                threshold_critical=metric_data.get("threshold_critical"),
                enabled=metric_data.get("enabled", True),
            )

        for rule_id, rule_data in data.get("alert_rules", {}).items():
            config.alert_rules[rule_id] = AlertRule(
                rule_id=rule_data["rule_id"],
                metric_name=rule_data["metric_name"],
                condition=rule_data["condition"],
                threshold=rule_data["threshold"],
                severity=AlertSeverity(rule_data["severity"]),
                message=rule_data["message"],
                enabled=rule_data.get("enabled", True),
            )

        config.trend_windows = data.get("trend_windows", config.trend_windows)

        logger.info(f"Loaded dashboard config from {filepath}")
        return config


# Global dashboard config instance
_dashboard_config: Optional[DashboardConfig] = None


def get_dashboard_config() -> DashboardConfig:
    """Get the global dashboard config instance."""
    global _dashboard_config
    if _dashboard_config is None:
        _dashboard_config = DashboardConfig()
    return _dashboard_config


__all__ = [
    "DashboardConfig",
    "MetricDefinition",
    "AlertRule",
    "MetricType",
    "AlertSeverity",
    "get_dashboard_config",
]