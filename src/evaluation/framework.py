"""Comprehensive RAG Evaluation Framework.

This module provides:
- RAGAS metric integration
- Custom agent metrics
- Baseline establishment
- CI/CD integration

Usage:
    from evaluation.framework import RAGEvaluationFramework

    framework = RAGEvaluationFramework()
    results = await framework.evaluate_pipeline(
        queries=test_queries,
        rag_pipeline=rag_handler
    )
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from evaluation.service import RAGASEvaluationService, get_evaluation_service
from models.evaluation import (
    EvaluationRequest,
    EvaluationMetric,
    EvaluationResponse,
)
from config.config import settings

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of evaluation metrics."""

    RAGAS = "ragas"  # Standard RAGAS metrics
    AGENT = "agent"  # Agent-specific metrics
    GRAPH = "graph"  # Graph execution metrics
    USER = "user"  # User satisfaction metrics
    COST = "cost"  # Cost per query


@dataclass
class AgentMetric:
    """Agent-specific evaluation metric.

    Attributes:
        name: Metric name
        value: Metric value (0-1 for scores, variable for counters)
        threshold: Minimum acceptable value
        passed: Whether metric meets threshold
        metadata: Additional context
    """

    name: str
    value: float
    threshold: float
    passed: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "threshold": self.threshold,
            "passed": self.passed,
            "metadata": self.metadata,
        }


@dataclass
class GraphMetric:
    """Graph execution metrics.

    Attributes:
        iteration_count: Number of graph iterations
        retry_count: Number of retries
        total_latency_ms: Total execution time
        agent_breakdown: Time spent per agent
        decision_points: Number of branching decisions
    """

    iteration_count: int = 0
    retry_count: int = 0
    total_latency_ms: float = 0.0
    agent_breakdown: dict[str, float] = field(default_factory=dict)
    decision_points: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "iteration_count": self.iteration_count,
            "retry_count": self.retry_count,
            "total_latency_ms": self.total_latency_ms,
            "agent_breakdown": self.agent_breakdown,
            "decision_points": self.decision_points,
        }


@dataclass
class UserFeedbackMetric:
    """User satisfaction metrics.

    Attributes:
        thumbs_up: Number of positive ratings
        thumbs_down: Number of negative ratings
        total_ratings: Total number of ratings
        satisfaction_rate: Ratio of positive ratings
        average_rating: Average rating (1-5 scale)
    """

    thumbs_up: int = 0
    thumbs_down: int = 0
    total_ratings: int = 0
    satisfaction_rate: float = 0.0
    average_rating: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "thumbs_up": self.thumbs_up,
            "thumbs_down": self.thumbs_down,
            "total_ratings": self.total_ratings,
            "satisfaction_rate": self.satisfaction_rate,
            "average_rating": self.average_rating,
        }


@dataclass
class CostMetric:
    """Cost tracking metrics.

    Attributes:
        llm_input_tokens: Total input tokens
        llm_output_tokens: Total output tokens
        embedding_tokens: Total embedding tokens
        estimated_cost_usd: Estimated cost in USD
        cost_per_query: Average cost per query
    """

    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    embedding_tokens: int = 0
    estimated_cost_usd: float = 0.0
    cost_per_query: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "llm_input_tokens": self.llm_input_tokens,
            "llm_output_tokens": self.llm_output_tokens,
            "embedding_tokens": self.embedding_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "cost_per_query": self.cost_per_query,
        }


@dataclass
class ComprehensiveEvaluationResult:
    """Comprehensive evaluation result.

    Attributes:
        evaluation_id: Unique evaluation ID
        timestamp: Evaluation timestamp
        ragas_results: RAGAS metric results
        agent_metrics: Agent-specific metrics
        graph_metrics: Graph execution metrics
        user_feedback: User satisfaction metrics
        cost_metrics: Cost tracking metrics
        overall_score: Overall aggregated score
        passed_baseline: Whether evaluation passes baseline
    """

    evaluation_id: str
    timestamp: datetime
    ragas_results: list[EvaluationResponse]
    agent_metrics: list[AgentMetric]
    graph_metrics: GraphMetric
    user_feedback: UserFeedbackMetric
    cost_metrics: CostMetric
    overall_score: float
    passed_baseline: bool
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "evaluation_id": self.evaluation_id,
            "timestamp": self.timestamp.isoformat(),
            "ragas_results": [
                {
                    "evaluation_id": r.evaluation_id,
                    "query": r.query,
                    "overall_score": r.overall_score,
                    "results": [
                        {
                            "metric": rr.metric.value,
                            "score": rr.score,
                            "reasoning": rr.reasoning,
                            "error": rr.error,
                        }
                        for rr in r.results
                    ],
                }
                for r in self.ragas_results
            ],
            "agent_metrics": [am.to_dict() for am in self.agent_metrics],
            "graph_metrics": self.graph_metrics.to_dict(),
            "user_feedback": self.user_feedback.to_dict(),
            "cost_metrics": self.cost_metrics.to_dict(),
            "overall_score": self.overall_score,
            "passed_baseline": self.passed_baseline,
            "recommendations": self.recommendations,
        }


class BaselineConfig:
    """Baseline configuration for evaluation.

    Attributes:
        min_faithfulness: Minimum faithfulness score
        min_answer_relevancy: Minimum answer relevancy score
        min_context_precision: Minimum context precision score
        min_context_recall: Minimum context recall score
        max_latency_ms: Maximum acceptable latency
        max_cost_per_query_usd: Maximum cost per query
        min_satisfaction_rate: Minimum user satisfaction rate
    """

    def __init__(
        self,
        min_faithfulness: float = 0.7,
        min_answer_relevancy: float = 0.7,
        min_context_precision: float = 0.7,
        min_context_recall: float = 0.7,
        max_latency_ms: float = 5000.0,
        max_cost_per_query_usd: float = 0.01,
        min_satisfaction_rate: float = 0.8,
    ):
        self.min_faithfulness = min_faithfulness
        self.min_answer_relevancy = min_answer_relevancy
        self.min_context_precision = min_context_precision
        self.min_context_recall = min_context_recall
        self.max_latency_ms = max_latency_ms
        self.max_cost_per_query_usd = max_cost_per_query_usd
        self.min_satisfaction_rate = min_satisfaction_rate

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "min_faithfulness": self.min_faithfulness,
            "min_answer_relevancy": self.min_answer_relevancy,
            "min_context_precision": self.min_context_precision,
            "min_context_recall": self.min_context_recall,
            "max_latency_ms": self.max_latency_ms,
            "max_cost_per_query_usd": self.max_cost_per_query_usd,
            "min_satisfaction_rate": self.min_satisfaction_rate,
        }


class RAGEvaluationFramework:
    """Comprehensive RAG evaluation framework.

    This framework integrates RAGAS metrics with custom agent metrics,
    graph execution metrics, user feedback, and cost tracking.
    """

    def __init__(
        self,
        ragas_service: Optional[RAGASEvaluationService] = None,
        baseline_config: Optional[BaselineConfig] = None,
    ):
        """Initialize evaluation framework.

        Args:
            ragas_service: RAGAS evaluation service (optional)
            baseline_config: Baseline configuration (optional)
        """
        self.ragas_service = ragas_service or get_evaluation_service()
        self.baseline = baseline_config or BaselineConfig()
        self._evaluation_history: list[ComprehensiveEvaluationResult] = []

    async def evaluate_query(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ragas_metrics: Optional[list[EvaluationMetric]] = None,
        graph_metrics: Optional[GraphMetric] = None,
        user_feedback: Optional[UserFeedbackMetric] = None,
        cost_metrics: Optional[CostMetric] = None,
    ) -> ComprehensiveEvaluationResult:
        """Evaluate a single query comprehensively.

        Args:
            query: User query
            answer: Generated answer
            contexts: Retrieved contexts
            ragas_metrics: RAGAS metrics to evaluate
            graph_metrics: Graph execution metrics
            user_feedback: User feedback metrics
            cost_metrics: Cost metrics

        Returns:
            ComprehensiveEvaluationResult
        """
        evaluation_id = f"eval-{int(time.time())}"
        timestamp = datetime.utcnow()

        # Evaluate RAGAS metrics
        if ragas_metrics is None:
            ragas_metrics = [
                EvaluationMetric.FAITHFULNESS,
                EvaluationMetric.ANSWER_RELEVANCY,
                EvaluationMetric.CONTEXT_PRECISION,
                EvaluationMetric.CONTEXT_RECALL,
            ]

        ragas_request = EvaluationRequest(
            query=query,
            answer=answer,
            contexts=contexts,
            metrics=ragas_metrics,
        )

        ragas_response = await self.ragas_service.evaluate(ragas_request)

        # Calculate agent metrics
        agent_metrics = self._calculate_agent_metrics(
            ragas_response, graph_metrics, user_feedback, cost_metrics
        )

        # Default metrics
        if graph_metrics is None:
            graph_metrics = GraphMetric()
        if user_feedback is None:
            user_feedback = UserFeedbackMetric()
        if cost_metrics is None:
            cost_metrics = CostMetric()

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            ragas_response, agent_metrics, graph_metrics, user_feedback, cost_metrics
        )

        # Check baseline
        passed_baseline = self._check_baseline(
            ragas_response, graph_metrics, user_feedback, cost_metrics
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            ragas_response, agent_metrics, graph_metrics, user_feedback, cost_metrics
        )

        result = ComprehensiveEvaluationResult(
            evaluation_id=evaluation_id,
            timestamp=timestamp,
            ragas_results=[ragas_response],
            agent_metrics=agent_metrics,
            graph_metrics=graph_metrics,
            user_feedback=user_feedback,
            cost_metrics=cost_metrics,
            overall_score=overall_score,
            passed_baseline=passed_baseline,
            recommendations=recommendations,
        )

        self._evaluation_history.append(result)
        return result

    def _calculate_agent_metrics(
        self,
        ragas_response: EvaluationResponse,
        graph_metrics: Optional[GraphMetric],
        user_feedback: Optional[UserFeedbackMetric],
        cost_metrics: Optional[CostMetric],
    ) -> list[AgentMetric]:
        """Calculate agent-specific metrics."""
        metrics = []

        # Refiner success rate (faithfulness)
        faithfulness = next(
            (r for r in ragas_response.results if r.metric == EvaluationMetric.FAITHFULNESS), None
        )
        if faithfulness:
            metrics.append(
                AgentMetric(
                    name="refiner_success_rate",
                    value=faithfulness.score,
                    threshold=self.baseline.min_faithfulness,
                    passed=faithfulness.score >= self.baseline.min_faithfulness,
                    metadata={"reasoning": faithfulness.reasoning},
                )
            )

        # Retrieval accuracy (context precision)
        context_precision = next(
            (r for r in ragas_response.results if r.metric == EvaluationMetric.CONTEXT_PRECISION),
            None,
        )
        if context_precision:
            metrics.append(
                AgentMetric(
                    name="retrieval_accuracy",
                    value=context_precision.score,
                    threshold=self.baseline.min_context_precision,
                    passed=context_precision.score >= self.baseline.min_context_precision,
                    metadata={"reasoning": context_precision.reasoning},
                )
            )

        # Answer quality (answer relevancy)
        answer_relevancy = next(
            (r for r in ragas_response.results if r.metric == EvaluationMetric.ANSWER_RELEVANCY),
            None,
        )
        if answer_relevancy:
            metrics.append(
                AgentMetric(
                    name="answer_quality",
                    value=answer_relevancy.score,
                    threshold=self.baseline.min_answer_relevancy,
                    passed=answer_relevancy.score >= self.baseline.min_answer_relevancy,
                    metadata={"reasoning": answer_relevancy.reasoning},
                )
            )

        # Graph efficiency (retry rate)
        if graph_metrics:
            retry_rate = (
                graph_metrics.retry_count / max(graph_metrics.iteration_count, 1)
                if graph_metrics.iteration_count > 0
                else 0
            )
            metrics.append(
                AgentMetric(
                    name="graph_efficiency",
                    value=1.0 - retry_rate,  # Higher is better
                    threshold=0.8,  # 80% efficiency
                    passed=retry_rate < 0.2,  # Less than 20% retry rate
                    metadata={
                        "retry_count": graph_metrics.retry_count,
                        "iteration_count": graph_metrics.iteration_count,
                    },
                )
            )

        return metrics

    def _calculate_overall_score(
        self,
        ragas_response: EvaluationResponse,
        agent_metrics: list[AgentMetric],
        graph_metrics: GraphMetric,
        user_feedback: UserFeedbackMetric,
        cost_metrics: CostMetric,
    ) -> float:
        """Calculate overall score (0-1)."""
        # Weighted average
        weights = {
            "ragas": 0.5,  # 50% weight for RAGAS metrics
            "agent": 0.2,  # 20% weight for agent metrics
            "graph": 0.1,  # 10% weight for graph metrics
            "user": 0.1,  # 10% weight for user feedback
            "cost": 0.1,  # 10% weight for cost efficiency
        }

        # RAGAS score
        ragas_score = ragas_response.overall_score

        # Agent score
        if agent_metrics:
            agent_score = sum(m.value for m in agent_metrics) / len(agent_metrics)
        else:
            agent_score = 0.0

        # Graph score (based on efficiency)
        graph_efficiency = (
            1.0
            - (graph_metrics.retry_count / max(graph_metrics.iteration_count, 1))
            if graph_metrics.iteration_count > 0
            else 1.0
        )
        graph_score = graph_efficiency

        # User score
        user_score = user_feedback.satisfaction_rate

        # Cost score (inverse - lower cost is better)
        cost_score = (
            max(0.0, 1.0 - (cost_metrics.cost_per_query / self.baseline.max_cost_per_query_usd))
            if self.baseline.max_cost_per_query_usd > 0
            else 1.0
        )

        overall = (
            weights["ragas"] * ragas_score
            + weights["agent"] * agent_score
            + weights["graph"] * graph_score
            + weights["user"] * user_score
            + weights["cost"] * cost_score
        )

        return round(overall, 3)

    def _check_baseline(
        self,
        ragas_response: EvaluationResponse,
        graph_metrics: GraphMetric,
        user_feedback: UserFeedbackMetric,
        cost_metrics: CostMetric,
    ) -> bool:
        """Check if evaluation meets baseline criteria."""
        # Check RAGAS metrics
        for result in ragas_response.results:
            if result.error is not None:
                logger.warning(f"RAGAS metric {result.metric.value} had error: {result.error}")
                continue

            if result.metric == EvaluationMetric.FAITHFULNESS:
                if result.score < self.baseline.min_faithfulness:
                    logger.info(f"Faithfulness {result.score:.2f} below baseline {self.baseline.min_faithfulness}")
                    return False
            elif result.metric == EvaluationMetric.ANSWER_RELEVANCY:
                if result.score < self.baseline.min_answer_relevancy:
                    logger.info(f"Answer relevancy {result.score:.2f} below baseline {self.baseline.min_answer_relevancy}")
                    return False
            elif result.metric == EvaluationMetric.CONTEXT_PRECISION:
                if result.score < self.baseline.min_context_precision:
                    logger.info(f"Context precision {result.score:.2f} below baseline {self.baseline.min_context_precision}")
                    return False
            elif result.metric == EvaluationMetric.CONTEXT_RECALL:
                if result.score < self.baseline.min_context_recall:
                    logger.info(f"Context recall {result.score:.2f} below baseline {self.baseline.min_context_recall}")
                    return False

        # Check latency
        if graph_metrics.total_latency_ms > self.baseline.max_latency_ms:
            logger.info(f"Latency {graph_metrics.total_latency_ms:.2f}ms above baseline {self.baseline.max_latency_ms}ms")
            return False

        # Check cost
        if cost_metrics.cost_per_query > self.baseline.max_cost_per_query_usd:
            logger.info(f"Cost ${cost_metrics.cost_per_query:.4f} above baseline ${self.baseline.max_cost_per_query_usd:.4f}")
            return False

        # Check user satisfaction
        if user_feedback.total_ratings > 0:
            if user_feedback.satisfaction_rate < self.baseline.min_satisfaction_rate:
                logger.info(f"Satisfaction {user_feedback.satisfaction_rate:.2%} below baseline {self.baseline.min_satisfaction_rate:.2%}")
                return False

        return True

    def _generate_recommendations(
        self,
        ragas_response: EvaluationResponse,
        agent_metrics: list[AgentMetric],
        graph_metrics: GraphMetric,
        user_feedback: UserFeedbackMetric,
        cost_metrics: CostMetric,
    ) -> list[str]:
        """Generate improvement recommendations."""
        recommendations = []

        # Analyze RAGAS metrics
        for result in ragas_response.results:
            if result.error is not None:
                continue

            if result.metric == EvaluationMetric.FAITHFULNESS:
                if result.score < 0.7:
                    recommendations.append(
                        "Faithfulness low - Consider improving context grounding "
                        "or adding citation verification"
                    )
                elif result.score < 0.85:
                    recommendations.append(
                        "Faithfulness moderate - Review answer generation prompts"
                    )

            elif result.metric == EvaluationMetric.ANSWER_RELEVANCY:
                if result.score < 0.7:
                    recommendations.append(
                        "Answer relevancy low - Improve query understanding or retrieval"
                    )
                elif result.score < 0.85:
                    recommendations.append(
                        "Answer relevancy moderate - Fine-tune retrieval parameters"
                    )

            elif result.metric == EvaluationMetric.CONTEXT_PRECISION:
                if result.score < 0.7:
                    recommendations.append(
                        "Context precision low - Improve retrieval strategy or reranking"
                    )
                elif result.score < 0.85:
                    recommendations.append(
                        "Context precision moderate - Adjust retrieval threshold"
                    )

            elif result.metric == EvaluationMetric.CONTEXT_RECALL:
                if result.score < 0.7:
                    recommendations.append(
                        "Context recall low - Increase top-k or improve chunking"
                    )
                elif result.score < 0.85:
                    recommendations.append(
                        "Context recall moderate - Review document coverage"
                    )

        # Analyze graph metrics
        retry_rate = (
            graph_metrics.retry_count / max(graph_metrics.iteration_count, 1)
            if graph_metrics.iteration_count > 0
            else 0
        )
        if retry_rate > 0.2:
            recommendations.append(f"High retry rate ({retry_rate:.1%}) - Review graph logic")

        # Analyze cost
        if cost_metrics.cost_per_query > self.baseline.max_cost_per_query_usd:
            recommendations.append(f"High cost per query (${cost_metrics.cost_per_query:.4f}) - Optimize token usage")

        return recommendations

    async def evaluate_batch(
        self,
        queries: list[dict[str, Any]],
        concurrent_evaluations: int = 5,
    ) -> list[ComprehensiveEvaluationResult]:
        """Evaluate multiple queries in batch.

        Args:
            queries: List of query dicts with query, answer, contexts
            concurrent_evaluations: Number of concurrent evaluations

        Returns:
            List of ComprehensiveEvaluationResult
        """
        semaphore = asyncio.Semaphore(concurrent_evaluations)

        async def evaluate_single(q: dict) -> ComprehensiveEvaluationResult:
            async with semaphore:
                return await self.evaluate_query(
                    query=q["query"],
                    answer=q["answer"],
                    contexts=q["contexts"],
                )

        tasks = [evaluate_single(q) for q in queries]
        results = await asyncio.gather(*tasks)

        return results

    def get_evaluation_history(self) -> list[ComprehensiveEvaluationResult]:
        """Get evaluation history."""
        return self._evaluation_history

    def get_aggregated_metrics(self) -> dict[str, Any]:
        """Get aggregated metrics across all evaluations."""
        if not self._evaluation_history:
            return {}

        # Aggregate RAGAS metrics
        ragas_scores = defaultdict(list)
        for result in self._evaluation_history:
            for ragas_result in result.ragas_results:
                for metric_result in ragas_result.results:
                    if metric_result.error is None:
                        ragas_scores[metric_result.metric.value].append(metric_result.score)

        aggregated_ragas = {}
        for metric, scores in ragas_scores.items():
            aggregated_ragas[metric] = {
                "mean": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores),
                "count": len(scores),
            }

        # Aggregate overall scores
        overall_scores = [r.overall_score for r in self._evaluation_history]
        aggregated_overall = {
            "mean": sum(overall_scores) / len(overall_scores),
            "min": min(overall_scores),
            "max": max(overall_scores),
            "count": len(overall_scores),
        }

        # Baseline pass rate
        pass_count = sum(1 for r in self._evaluation_history if r.passed_baseline)
        pass_rate = pass_count / len(self._evaluation_history)

        return {
            "ragas_metrics": aggregated_ragas,
            "overall_score": aggregated_overall,
            "baseline_pass_rate": pass_rate,
            "total_evaluations": len(self._evaluation_history),
        }

    def save_results(self, filepath: str | Path) -> None:
        """Save evaluation results to JSON file.

        Args:
            filepath: Path to save results
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        results = [r.to_dict() for r in self._evaluation_history]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(results)} evaluation results to {filepath}")

    def load_results(self, filepath: str | Path) -> None:
        """Load evaluation results from JSON file.

        Args:
            filepath: Path to load results from
        """
        filepath = Path(filepath)

        if not filepath.exists():
            logger.warning(f"Results file not found: {filepath}")
            return

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Reconstruct evaluation results
        for item in data:
            # Note: This is a simplified reconstruction
            # In production, you'd need to properly reconstruct all objects
            result = ComprehensiveEvaluationResult(
                evaluation_id=item["evaluation_id"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                ragas_results=[],  # Would need full reconstruction
                agent_metrics=[],
                graph_metrics=GraphMetric(),
                user_feedback=UserFeedbackMetric(),
                cost_metrics=CostMetric(),
                overall_score=item["overall_score"],
                passed_baseline=item["passed_baseline"],
                recommendations=item.get("recommendations", []),
            )
            self._evaluation_history.append(result)

        logger.info(f"Loaded {len(data)} evaluation results from {filepath}")


__all__ = [
    "RAGEvaluationFramework",
    "BaselineConfig",
    "ComprehensiveEvaluationResult",
    "AgentMetric",
    "GraphMetric",
    "UserFeedbackMetric",
    "CostMetric",
    "MetricType",
]
