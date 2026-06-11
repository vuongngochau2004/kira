"""Custom metrics for Agentic RAG monitoring.

This module provides:
- Agent-specific metrics (refiner success rate, retrieval accuracy)
- Graph metrics (iteration count, retry rate)
- User satisfaction signals
- Cost per query tracking

Usage:
    from src.shared.infrastructure.monitoring.agentic_metrics import AgenticMetricsCollector

    collector = AgenticMetricsCollector()
    collector.record_agent_call(
        agent_name="RAGRouter",
        query="...",
        success=True,
        latency_ms=1234,
        metrics={"retrieval_count": 5}
    )
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from config.config import settings

logger = logging.getLogger(__name__)


class MetricCategory(Enum):
    """Categories of metrics."""
    PERFORMANCE = "performance"
    QUALITY = "quality"
    COST = "cost"
    USER = "user"


@dataclass
class AgentCallMetric:
    """Metric for a single agent call."""
    call_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_name: str = ""
    query: str = ""
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    success: bool = True
    latency_ms: float = 0.0
    error_message: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "call_id": self.call_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_name": self.agent_name,
            "query": self.query,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass
class GraphExecutionMetric:
    """Metric for graph execution."""
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    iteration_count: int = 0
    retry_count: int = 0
    total_latency_ms: float = 0.0
    agent_breakdown: dict[str, float] = field(default_factory=dict)
    decision_points: int = 0
    user_id: Optional[str] = None
    query: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "timestamp": self.timestamp.isoformat(),
            "iteration_count": self.iteration_count,
            "retry_count": self.retry_count,
            "total_latency_ms": self.total_latency_ms,
            "agent_breakdown": self.agent_breakdown,
            "decision_points": self.decision_points,
            "user_id": self.user_id,
            "query": self.query,
        }


@dataclass
class UserFeedbackMetric:
    """Metric for user feedback."""
    feedback_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    rating: Optional[int] = None
    feedback_type: str = "rating"
    comment: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feedback_id": self.feedback_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "rating": self.rating,
            "feedback_type": self.feedback_type,
            "comment": self.comment,
        }


@dataclass
class CostMetric:
    """Metric for cost tracking."""
    metric_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    query_id: Optional[str] = None
    user_id: Optional[str] = None
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    embedding_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_id": self.metric_id,
            "timestamp": self.timestamp.isoformat(),
            "query_id": self.query_id,
            "user_id": self.user_id,
            "llm_input_tokens": self.llm_input_tokens,
            "llm_output_tokens": self.llm_output_tokens,
            "embedding_tokens": self.embedding_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "model_name": self.model_name,
        }


class AgenticMetricsCollector:
    """Collector for agentic RAG metrics."""

    def __init__(self, retention_hours: int = 24):
        """Initialize metrics collector."""
        self.retention_hours = retention_hours
        self._agent_calls: list[AgentCallMetric] = []
        self._graph_executions: list[GraphExecutionMetric] = []
        self._user_feedbacks: list[UserFeedbackMetric] = []
        self._cost_metrics: list[CostMetric] = []

    def record_agent_call(
        self,
        agent_name: str,
        query: str,
        success: bool,
        latency_ms: float,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record an agent call metric."""
        metric = AgentCallMetric(
            agent_name=agent_name,
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            success=success,
            latency_ms=latency_ms,
            error_message=error_message,
            metadata=metadata or {},
        )
        self._agent_calls.append(metric)
        logger.debug(f"[METRICS] Recorded agent call: {agent_name} ({latency_ms:.2f}ms)")

    def record_graph_execution(
        self,
        iteration_count: int,
        retry_count: int,
        total_latency_ms: float,
        agent_breakdown: dict[str, float],
        decision_points: int,
        query: str,
        user_id: Optional[str] = None,
    ) -> None:
        """Record graph execution metric."""
        metric = GraphExecutionMetric(
            iteration_count=iteration_count,
            retry_count=retry_count,
            total_latency_ms=total_latency_ms,
            agent_breakdown=agent_breakdown,
            decision_points=decision_points,
            query=query,
            user_id=user_id,
        )
        self._graph_executions.append(metric)
        logger.debug(f"[METRICS] Recorded graph execution: {iteration_count} iterations, {retry_count} retries")

    def record_user_feedback(
        self,
        user_id: Optional[str],
        conversation_id: Optional[str],
        message_id: Optional[str],
        rating: Optional[int],
        feedback_type: str = "rating",
        comment: Optional[str] = None,
    ) -> None:
        """Record user feedback metric."""
        metric = UserFeedbackMetric(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            rating=rating,
            feedback_type=feedback_type,
            comment=comment,
        )
        self._user_feedbacks.append(metric)
        logger.debug(f"[METRICS] Recorded user feedback: {feedback_type} = {rating}")

    def record_cost(
        self,
        query_id: Optional[str],
        user_id: Optional[str],
        llm_input_tokens: int,
        llm_output_tokens: int,
        embedding_tokens: int,
        estimated_cost_usd: float,
        model_name: str,
    ) -> None:
        """Record cost metric."""
        metric = CostMetric(
            query_id=query_id,
            user_id=user_id,
            llm_input_tokens=llm_input_tokens,
            llm_output_tokens=llm_output_tokens,
            embedding_tokens=embedding_tokens,
            estimated_cost_usd=estimated_cost_usd,
            model_name=model_name,
        )
        self._cost_metrics.append(metric)
        logger.debug(f"[METRICS] Recorded cost: ${estimated_cost_usd:.4f} ({model_name})")

    def get_agent_metrics(
        self,
        agent_name: Optional[str] = None,
        time_window_hours: int = 1,
    ) -> dict[str, Any]:
        """Get aggregated agent metrics."""
        cutoff = datetime.utcnow() - timedelta(hours=time_window_hours)

        if agent_name:
            recent_calls = [
                m for m in self._agent_calls
                if m.agent_name == agent_name and m.timestamp > cutoff
            ]
        else:
            recent_calls = [m for m in self._agent_calls if m.timestamp > cutoff]

        if not recent_calls:
            return {"total_calls": 0}

        total_calls = len(recent_calls)
        successful_calls = sum(1 for m in recent_calls if m.success)
        failed_calls = total_calls - successful_calls

        latencies = [m.latency_ms for m in recent_calls if m.latency_ms > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else (latencies[0] if latencies else 0),
        }

    def get_graph_metrics(self, time_window_hours: int = 1) -> dict[str, Any]:
        """Get aggregated graph metrics."""
        cutoff = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_executions = [m for m in self._graph_executions if m.timestamp > cutoff]

        if not recent_executions:
            return {"total_executions": 0}

        total_executions = len(recent_executions)
        total_iterations = sum(m.iteration_count for m in recent_executions)
        total_retries = sum(m.retry_count for m in recent_executions)
        avg_iterations = total_iterations / total_executions if total_executions > 0 else 0
        avg_retries = total_retries / total_executions if total_executions > 0 else 0

        agent_times = defaultdict(list)
        for metric in recent_executions:
            for agent, time_ms in metric.agent_breakdown.items():
                agent_times[agent].append(time_ms)

        agent_breakdown = {}
        for agent, times in agent_times.items():
            agent_breakdown[agent] = {
                "avg_time_ms": sum(times) / len(times),
                "total_calls": len(times),
            }

        return {
            "total_executions": total_executions,
            "avg_iterations": avg_iterations,
            "avg_retries": avg_retries,
            "retry_rate": avg_retries / avg_iterations if avg_iterations > 0 else 0,
            "agent_breakdown": agent_breakdown,
        }

    def get_user_satisfaction(self, time_window_hours: int = 24) -> dict[str, Any]:
        """Get user satisfaction metrics."""
        cutoff = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_feedback = [m for m in self._user_feedbacks if m.timestamp > cutoff]

        if not recent_feedback:
            return {"total_feedback": 0}

        total_feedback = len(recent_feedback)
        thumbs_up = sum(1 for m in recent_feedback if m.feedback_type == "thumbs_up")
        thumbs_down = sum(1 for m in recent_feedback if m.feedback_type == "thumbs_down")
        ratings = [m.rating for m in recent_feedback if m.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        satisfaction_rate = thumbs_up / (thumbs_up + thumbs_down) if (thumbs_up + thumbs_down) > 0 else 0

        return {
            "total_feedback": total_feedback,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "satisfaction_rate": satisfaction_rate,
            "avg_rating": avg_rating,
            "total_ratings": len(ratings),
        }

    def get_cost_metrics(self, time_window_hours: int = 24) -> dict[str, Any]:
        """Get cost metrics."""
        cutoff = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_costs = [m for m in self._cost_metrics if m.timestamp > cutoff]

        if not recent_costs:
            return {"total_queries": 0}

        total_queries = len(recent_costs)
        total_cost = sum(m.estimated_cost_usd for m in recent_costs)
        avg_cost_per_query = total_cost / total_queries if total_queries > 0 else 0

        total_llm_input = sum(m.llm_input_tokens for m in recent_costs)
        total_llm_output = sum(m.llm_output_tokens for m in recent_costs)
        total_embedding = sum(m.embedding_tokens for m in recent_costs)
        total_tokens = total_llm_input + total_llm_output + total_embedding

        return {
            "total_queries": total_queries,
            "total_cost_usd": total_cost,
            "avg_cost_per_query_usd": avg_cost_per_query,
            "total_tokens": total_tokens,
            "total_llm_input_tokens": total_llm_input,
            "total_llm_output_tokens": total_llm_output,
            "total_embedding_tokens": total_embedding,
        }

    def get_all_metrics(self, time_window_hours: int = 1) -> dict[str, Any]:
        """Get all aggregated metrics."""
        return {
            "agent": self.get_agent_metrics(time_window_hours=time_window_hours),
            "graph": self.get_graph_metrics(time_window_hours=time_window_hours),
            "user": self.get_user_satisfaction(time_window_hours=time_window_hours),
            "cost": self.get_cost_metrics(time_window_hours=time_window_hours),
        }

    def get_agent_specific_metrics(self, agent_name: str) -> dict[str, Any]:
        """Get agent-specific metrics."""
        agent_calls = [m for m in self._agent_calls if m.agent_name == agent_name]

        if not agent_calls:
            return {"agent_name": agent_name, "total_calls": 0}

        total_calls = len(agent_calls)
        successful_calls = sum(1 for m in agent_calls if m.success)
        success_rate = successful_calls / total_calls if total_calls > 0 else 0

        latencies = [m.latency_ms for m in agent_calls if m.latency_ms > 0]
        latency_stats = {}
        if latencies:
            latencies_sorted = sorted(latencies)
            latency_stats = {
                "avg": sum(latencies) / len(latencies),
                "p50": latencies_sorted[int(len(latencies) * 0.5)],
                "p95": latencies_sorted[int(len(latencies) * 0.95)],
                "p99": latencies_sorted[int(len(latencies) * 0.99)],
            }

        errors = [m.error_message for m in agent_calls if not m.success and m.error_message]
        error_counts = defaultdict(int)
        for error in errors:
            error_counts[error] += 1

        return {
            "agent_name": agent_name,
            "total_calls": total_calls,
            "success_rate": success_rate,
            "latency_stats": latency_stats,
            "error_counts": dict(error_counts),
        }

    def export_metrics(self, filepath: str) -> None:
        """Export all metrics to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "agent_calls": [m.to_dict() for m in self._agent_calls],
            "graph_executions": [m.to_dict() for m in self._graph_executions],
            "user_feedbacks": [m.to_dict() for m in self._user_feedbacks],
            "cost_metrics": [m.to_dict() for m in self._cost_metrics],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported metrics to {filepath}")

    def clear_old_data(self) -> int:
        """Clear data beyond retention period."""
        cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)

        agent_count = len(self._agent_calls)
        graph_count = len(self._graph_executions)
        feedback_count = len(self._user_feedbacks)
        cost_count = len(self._cost_metrics)

        self._agent_calls = [m for m in self._agent_calls if m.timestamp > cutoff]
        self._graph_executions = [m for m in self._graph_executions if m.timestamp > cutoff]
        self._user_feedbacks = [m for m in self._user_feedbacks if m.timestamp > cutoff]
        self._cost_metrics = [m for m in self._cost_metrics if m.timestamp > cutoff]

        cleared = (
            (agent_count - len(self._agent_calls))
            + (graph_count - len(self._graph_executions))
            + (feedback_count - len(self._user_feedbacks))
            + (cost_count - len(self._cost_metrics))
        )

        logger.info(f"Cleared {cleared} old metric records")
        return cleared


# Global metrics collector instance
_agentic_metrics_collector: Optional[AgenticMetricsCollector] = None


def get_agentic_metrics_collector() -> AgenticMetricsCollector:
    """Get the global agentic metrics collector instance."""
    global _agentic_metrics_collector
    if _agentic_metrics_collector is None:
        _agentic_metrics_collector = AgenticMetricsCollector()
    return _agentic_metrics_collector


__all__ = [
    "AgenticMetricsCollector",
    "AgentCallMetric",
    "GraphExecutionMetric",
    "UserFeedbackMetric",
    "CostMetric",
    "MetricCategory",
    "get_agentic_metrics_collector",
]