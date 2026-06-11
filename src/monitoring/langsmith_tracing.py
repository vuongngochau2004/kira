"""LangSmith tracing integration for Agentic RAG.

This module provides:
- LangSmith trace configuration
- Automatic tracing of agent calls, decisions, and errors
- Cost tracking
- Performance monitoring

Usage:
    from monitoring.langsmith_tracing import LangSmithTracer

    tracer = LangSmithTracer()
    with tracer.trace_agent("RAGRouter", query="..."):
        result = await router.handle(...)
"""

import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import uuid4

from config.config import settings

logger = logging.getLogger(__name__)


class TraceType(Enum):
    """Types of traces to capture."""

    AGENT_CALL = "agent_call"
    ROUTING_DECISION = "routing_decision"
    RETRIEVAL = "retrieval"
    LLM_CALL = "llm_call"
    GENERATION = "generation"
    ERROR = "error"


@dataclass
class TraceMetadata:
    """Metadata for LangSmith traces."""

    trace_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trace_type: TraceType = TraceType.AGENT_CALL
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    query: Optional[str] = None
    agent_name: Optional[str] = None
    latency_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None

    # Cost tracking
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Performance metrics
    retrieval_count: int = 0
    context_length: int = 0
    confidence_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "trace_type": self.trace_type.value,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "query": self.query,
            "agent_name": self.agent_name,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error_message": self.error_message,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "retrieval_count": self.retrieval_count,
            "context_length": self.context_length,
            "confidence_score": self.confidence_score,
        }


class LangSmithTracer:
    """LangSmith tracing integration.

    This tracer captures comprehensive traces of agent execution,
    including routing decisions, LLM calls, retrieval operations,
    and error conditions.

    In production, this would send data to LangSmith API.
    For now, it logs locally for development and testing.
    """

    def __init__(
        self,
        enabled: Optional[bool] = None,
        project_name: Optional[str] = None,
        sampling_rate: float = 1.0,
    ):
        """Initialize LangSmith tracer.

        Args:
            enabled: Enable tracing (None = check env var)
            project_name: LangSmith project name
            sampling_rate: Sampling rate (0.0-1.0)
        """
        self.enabled = enabled if enabled is not None else os.getenv("LANGCHAIN_TRACING_V2") == "true"
        self.project_name = project_name or os.getenv("LANGCHAIN_PROJECT", "kira-rag")
        self.sampling_rate = sampling_rate

        self._trace_stack: list[TraceMetadata] = []
        self._trace_history: list[dict[str, Any]] = []

        if not self.enabled:
            logger.info("LangSmith tracing disabled")
        else:
            logger.info(f"LangSmith tracing enabled (project: {self.project_name})")

    def trace_agent(
        self,
        agent_name: str,
        query: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ):
        """Context manager for tracing agent calls.

        Args:
            agent_name: Name of the agent
            query: User query
            user_id: User ID
            conversation_id: Conversation ID

        Returns:
            Context manager that yields trace metadata

        Example:
            with tracer.trace_agent("RAGRouter", query="...", user_id="..."):
                result = await router.handle(query, user_id)
        """
        return TraceContext(
            tracer=self,
            trace_type=TraceType.AGENT_CALL,
            agent_name=agent_name,
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
        )

    def trace_routing(
        self,
        query: str,
        router_name: str,
        confidence: float,
        user_id: Optional[str] = None,
    ):
        """Trace routing decisions.

        Args:
            query: User query
            router_name: Selected router name
            confidence: Routing confidence score
            user_id: User ID

        Returns:
            Context manager
        """
        return TraceContext(
            tracer=self,
            trace_type=TraceType.ROUTING_DECISION,
            agent_name=router_name,
            query=query,
            user_id=user_id,
            confidence_score=confidence,
        )

    def trace_retrieval(
        self,
        query: str,
        retrieval_count: int,
        context_length: int,
        user_id: Optional[str] = None,
    ):
        """Trace retrieval operations.

        Args:
            query: User query
            retrieval_count: Number of documents retrieved
            context_length: Total context length
            user_id: User ID

        Returns:
            Context manager
        """
        return TraceContext(
            tracer=self,
            trace_type=TraceType.RETRIEVAL,
            query=query,
            user_id=user_id,
            retrieval_count=retrieval_count,
            context_length=context_length,
        )

    def trace_llm(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float,
        query: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Trace LLM calls.

        Args:
            model_name: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            estimated_cost_usd: Estimated cost in USD
            query: User query
            user_id: User ID

        Returns:
            Context manager
        """
        return TraceContext(
            tracer=self,
            trace_type=TraceType.LLM_CALL,
            agent_name=model_name,
            query=query,
            user_id=user_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )

    def trace_generation(
        self,
        query: str,
        answer_length: int,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ):
        """Trace answer generation.

        Args:
            query: User query
            answer_length: Length of generated answer
            user_id: User ID
            conversation_id: Conversation ID

        Returns:
            Context manager
        """
        return TraceContext(
            tracer=self,
            trace_type=TraceType.GENERATION,
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            context_length=answer_length,
        )

    def trace_error(
        self,
        error_message: str,
        query: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ):
        """Trace errors.

        Args:
            error_message: Error message
            query: User query
            user_id: User ID
            agent_name: Agent that caused the error

        Returns:
            Context manager
        """
        return TraceContext(
            tracer=self,
            trace_type=TraceType.ERROR,
            query=query,
            user_id=user_id,
            agent_name=agent_name,
            success=False,
            error_message=error_message,
        )

    def _start_trace(self, metadata: TraceMetadata) -> None:
        """Start a new trace.

        Args:
            metadata: Trace metadata
        """
        if not self.enabled:
            return

        self._trace_stack.append(metadata)
        logger.debug(f"[LANGSMITH] Starting trace: {metadata.trace_type.value} ({metadata.trace_id})")

    def _end_trace(self, metadata: TraceMetadata) -> None:
        """End a trace and record it.

        Args:
            metadata: Trace metadata
        """
        if not self.enabled:
            return

        if not self._trace_stack:
            logger.warning("[LANGSMITH] No active trace to end")
            return

        # Pop from stack (should be same as passed in)
        current = self._trace_stack.pop()

        # Update latency
        metadata.latency_ms = (datetime.utcnow() - metadata.timestamp).total_seconds() * 1000

        # Add to history
        self._trace_history.append(metadata.to_dict())

        logger.debug(
            f"[LANGSMITH] Ended trace: {metadata.trace_type.value} "
            f"({metadata.trace_id}) in {metadata.latency_ms:.2f}ms"
        )

        # In production, send to LangSmith API
        # self._send_to_langsmith(metadata)

    def get_trace_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get trace history.

        Args:
            limit: Maximum number of traces to return

        Returns:
            List of trace dictionaries
        """
        return self._trace_history[-limit:]

    def get_aggregated_metrics(self, time_window_hours: int = 24) -> dict[str, Any]:
        """Get aggregated metrics from traces.

        Args:
            time_window_hours: Time window in hours

        Returns:
            Aggregated metrics dictionary
        """
        if not self._trace_history:
            return {}

        # Filter by time window
        cutoff = datetime.utcnow().timestamp() - (time_window_hours * 3600)
        recent_traces = [
            t
            for t in self._trace_history
            if datetime.fromisoformat(t["timestamp"]).timestamp() > cutoff
        ]

        if not recent_traces:
            return {}

        # Aggregate by trace type
        traces_by_type = defaultdict(list)
        for trace in recent_traces:
            traces_by_type[trace["trace_type"]].append(trace)

        # Calculate metrics
        metrics = {
            "total_traces": len(recent_traces),
            "by_type": {},
            "performance": {},
            "costs": {},
        }

        for trace_type, traces in traces_by_type.items():
            metrics["by_type"][trace_type] = len(traces)

        # Performance metrics
        latencies = [t["latency_ms"] for t in recent_traces if t["latency_ms"] > 0]
        if latencies:
            metrics["performance"] = {
                "avg_latency_ms": sum(latencies) / len(latencies),
                "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0],
                "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0],
            }

        # Error rate
        errors = [t for t in recent_traces if not t["success"]]
        metrics["performance"]["error_rate"] = len(errors) / len(recent_traces) if recent_traces else 0

        # Cost metrics
        llm_traces = traces_by_type.get("llm_call", [])
        if llm_traces:
            total_cost = sum(t["estimated_cost_usd"] for t in llm_traces)
            metrics["costs"] = {
                "total_cost_usd": total_cost,
                "avg_cost_per_call_usd": total_cost / len(llm_traces) if llm_traces else 0,
                "total_input_tokens": sum(t["input_tokens"] for t in llm_traces),
                "total_output_tokens": sum(t["output_tokens"] for t in llm_traces),
            }

        return metrics

    def export_traces(self, filepath: str) -> None:
        """Export traces to JSON file.

        Args:
            filepath: Path to export file
        """
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._trace_history, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported {len(self._trace_history)} traces to {filepath}")

    def clear_history(self) -> int:
        """Clear trace history.

        Returns:
            Number of traces cleared
        """
        count = len(self._trace_history)
        self._trace_history.clear()
        return count


class TraceContext:
    """Context manager for tracing operations."""

    def __init__(
        self,
        tracer: LangSmithTracer,
        trace_type: TraceType,
        agent_name: Optional[str] = None,
        query: Optional[str] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        confidence_score: float = 0.0,
        retrieval_count: int = 0,
        context_length: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """Initialize trace context.

        Args:
            tracer: LangSmith tracer instance
            trace_type: Type of trace
            agent_name: Agent name
            query: User query
            user_id: User ID
            conversation_id: Conversation ID
            confidence_score: Confidence score (0-1)
            retrieval_count: Number of retrievals
            context_length: Context length
            input_tokens: Input token count
            output_tokens: Output token count
            estimated_cost_usd: Estimated cost
            success: Whether operation succeeded
            error_message: Error message if failed
        """
        self.tracer = tracer
        self.metadata = TraceMetadata(
            trace_type=trace_type,
            agent_name=agent_name,
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            confidence_score=confidence_score,
            retrieval_count=retrieval_count,
            context_length=context_length,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            success=success,
            error_message=error_message,
        )
        self.start_time: Optional[float] = None

    def __enter__(self) -> TraceMetadata:
        """Enter trace context."""
        self.start_time = time.time()
        self.tracer._start_trace(self.metadata)
        return self.metadata

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit trace context."""
        # Update latency
        if self.start_time:
            self.metadata.latency_ms = (time.time() - self.start_time) * 1000

        # Check for exceptions
        if exc_type is not None:
            self.metadata.success = False
            self.metadata.error_message = str(exc_val)

        self.tracer._end_trace(self.metadata)

        # Don't suppress exceptions
        return False


# Global tracer instance
_langsmith_tracer: Optional[LangSmithTracer] = None


def get_langsmith_tracer() -> LangSmithTracer:
    """Get the global LangSmith tracer instance.

    Returns:
        LangSmithTracer instance
    """
    global _langsmith_tracer
    if _langsmith_tracer is None:
        _langsmith_tracer = LangSmithTracer()
    return _langsmith_tracer


__all__ = [
    "LangSmithTracer",
    "TraceType",
    "TraceMetadata",
    "TraceContext",
    "get_langsmith_tracer",
]
