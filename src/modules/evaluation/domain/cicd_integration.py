"""CI/CD integration for RAG evaluation.

This module provides:
- Automated evaluation in CI/CD pipeline
- Baseline comparison
- Regression detection
- Quality gate enforcement

Usage:
    from evaluation.ci_cd_integration import CICDEvaluator

    evaluator = CICDEvaluator()
    result = await evaluator.run_ci_evaluation(
        test_dataset="tests/data/rag_test_set.json",
        baseline_path="baselines/production_baseline.json"
    )
"""

import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from evaluation.framework import (
    RAGEvaluationFramework,
    BaselineConfig,
    ComprehensiveEvaluationResult,
)
from src.shared.infrastructure.monitoring.dashboard_config import DashboardConfig, AlertSeverity
from src.config.config import settings

logger = logging.getLogger(__name__)


class QualityGateStatus(Enum):
    """Quality gate status."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class QualityGateResult:
    """Result of quality gate evaluation.

    Attributes:
        gate_name: Name of the quality gate
        status: Gate status
        metrics: Actual metric values
        thresholds: Threshold values
        message: Result message
        details: Additional details
    """

    gate_name: str
    status: QualityGateStatus
    metrics: dict[str, float]
    thresholds: dict[str, float]
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gate_name": self.gate_name,
            "status": self.status.value,
            "metrics": self.metrics,
            "thresholds": self.thresholds,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class CICDResult:
    """Result of CI/CD evaluation.

    Attributes:
        run_id: Unique run ID
        timestamp: Evaluation timestamp
        git_commit: Git commit hash
        git_branch: Git branch name
        overall_status: Overall status
        quality_gates: Individual gate results
        comparison_baseline: Comparison with baseline
        regression_detected: Whether regression detected
        recommendations: Improvement recommendations
    """

    run_id: str
    timestamp: datetime
    git_commit: str
    git_branch: str
    overall_status: QualityGateStatus
    quality_gates: list[QualityGateResult]
    comparison_baseline: dict[str, Any]
    regression_detected: bool
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "overall_status": self.overall_status.value,
            "quality_gates": [gate.to_dict() for gate in self.quality_gates],
            "comparison_baseline": self.comparison_baseline,
            "regression_detected": self.regression_detected,
            "recommendations": self.recommendations,
        }


class CICDEvaluator:
    """CI/CD evaluator for automated RAG evaluation.

    This evaluator runs automated tests in CI/CD pipeline:
    1. Loads test dataset
    2. Runs evaluation queries
    3. Compares with baseline
    4. Checks quality gates
    5. Detects regressions
    """

    def __init__(
        self,
        framework: Optional[RAGEvaluationFramework] = None,
        baseline_config: Optional[BaselineConfig] = None,
        dashboard_config: Optional[DashboardConfig] = None,
    ):
        """Initialize CI/CD evaluator.

        Args:
            framework: Evaluation framework
            baseline_config: Baseline configuration
            dashboard_config: Dashboard configuration
        """
        self.framework = framework or RAGEvaluationFramework(baseline_config=baseline_config)
        self.dashboard_config = dashboard_config or DashboardConfig()

    async def run_ci_evaluation(
        self,
        test_dataset: str | Path,
        baseline_path: Optional[str | Path] = None,
        max_queries: int = 50,
        concurrent_evaluations: int = 5,
    ) -> CICDResult:
        """Run full CI/CD evaluation.

        Args:
            test_dataset: Path to test dataset JSON
            baseline_path: Path to baseline JSON (optional)
            max_queries: Maximum queries to evaluate
            concurrent_evaluations: Concurrent evaluations

        Returns:
            CICDResult with full evaluation results
        """
        run_id = f"ci-run-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        timestamp = datetime.utcnow()

        # Get git info
        git_commit = self._get_git_commit()
        git_branch = self._get_git_branch()

        logger.info(f"[CI/CD] Starting evaluation run {run_id}")
        logger.info(f"[CI/CD] Git commit: {git_commit}, branch: {git_branch}")

        # Load test dataset
        test_queries = self._load_test_dataset(test_dataset, max_queries)
        logger.info(f"[CI/CD] Loaded {len(test_queries)} test queries")

        # Run evaluation
        logger.info(f"[CI/CD] Running evaluation with {concurrent_evaluations} concurrent workers")
        results = await self.framework.evaluate_batch(
            queries=test_queries,
            concurrent_evaluations=concurrent_evaluations,
        )

        # Calculate aggregated metrics
        aggregated_metrics = self.framework.get_aggregated_metrics()
        logger.info(f"[CI/CD] Evaluation complete: {len(results)} queries evaluated")

        # Load baseline if provided
        baseline_metrics = {}
        if baseline_path:
            baseline_metrics = self._load_baseline(baseline_path)
            logger.info(f"[CI/CD] Loaded baseline with {len(baseline_metrics)} metrics")

        # Compare with baseline
        comparison = self._compare_with_baseline(aggregated_metrics, baseline_metrics)

        # Check quality gates
        quality_gates = self._check_quality_gates(aggregated_metrics)

        # Detect regressions
        regression_detected = self._detect_regressions(comparison)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            aggregated_metrics, comparison, quality_gates
        )

        # Determine overall status
        overall_status = self._determine_overall_status(quality_gates, regression_detected)

        result = CICDResult(
            run_id=run_id,
            timestamp=timestamp,
            git_commit=git_commit,
            git_branch=git_branch,
            overall_status=overall_status,
            quality_gates=quality_gates,
            comparison_baseline=comparison,
            regression_detected=regression_detected,
            recommendations=recommendations,
        )

        logger.info(f"[CI/CD] Evaluation complete: {overall_status.value}")
        return result

    def _load_test_dataset(
        self, filepath: str | Path, max_queries: int
    ) -> list[dict[str, Any]]:
        """Load test dataset from JSON file.

        Args:
            filepath: Path to test dataset
            max_queries: Maximum queries to load

        Returns:
            List of query dictionaries
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Test dataset not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Limit queries
        queries = data.get("queries", [])[:max_queries]

        # Validate format
        for i, query in enumerate(queries):
            if not all(key in query for key in ["query", "answer", "contexts"]):
                raise ValueError(f"Query {i} missing required fields")

        return queries

    def _load_baseline(self, filepath: str | Path) -> dict[str, float]:
        """Load baseline metrics from JSON file.

        Args:
            filepath: Path to baseline file

        Returns:
            Dictionary of baseline metrics
        """
        filepath = Path(filepath)

        if not filepath.exists():
            logger.warning(f"Baseline file not found: {filepath}")
            return {}

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("metrics", {})

    def _compare_with_baseline(
        self, current: dict[str, Any], baseline: dict[str, float]
    ) -> dict[str, Any]:
        """Compare current metrics with baseline.

        Args:
            current: Current metrics
            baseline: Baseline metrics

        Returns:
            Comparison results
        """
        comparison = {
            "improved": [],
            "degraded": [],
            "stable": [],
            "new": [],
        }

        # Compare RAGAS metrics
        current_ragas = current.get("ragas_metrics", {})

        for metric_name, baseline_value in baseline.items():
            if metric_name not in current_ragas:
                continue

            current_data = current_ragas[metric_name]
            current_value = current_data.get("mean", 0)

            diff = current_value - baseline_value
            diff_pct = (diff / baseline_value * 100) if baseline_value > 0 else 0

            if diff > 0.05:  # 5% improvement threshold
                comparison["improved"].append({
                    "metric": metric_name,
                    "baseline": baseline_value,
                    "current": current_value,
                    "diff": diff,
                    "diff_pct": diff_pct,
                })
            elif diff < -0.05:  # 5% degradation threshold
                comparison["degraded"].append({
                    "metric": metric_name,
                    "baseline": baseline_value,
                    "current": current_value,
                    "diff": diff,
                    "diff_pct": diff_pct,
                })
            else:
                comparison["stable"].append({
                    "metric": metric_name,
                    "baseline": baseline_value,
                    "current": current_value,
                })

        # Check for new metrics
        for metric_name in current_ragas:
            if metric_name not in baseline:
                comparison["new"].append({
                    "metric": metric_name,
                    "value": current_ragas[metric_name].get("mean", 0),
                })

        return comparison

    def _check_quality_gates(self, metrics: dict[str, Any]) -> list[QualityGateResult]:
        """Check quality gates against metrics.

        Args:
            metrics: Aggregated metrics

        Returns:
            List of quality gate results
        """
        gates = []

        # RAGAS quality gate
        ragas_metrics = metrics.get("ragas_metrics", {})
        gate_metrics = {}
        gate_thresholds = {}

        for metric_name, metric_data in ragas_metrics.items():
            metric_def = self.dashboard_config.get_metric_definition(metric_name)
            if metric_def:
                gate_metrics[metric_name] = metric_data.get("mean", 0)
                gate_thresholds[metric_name] = metric_def.threshold_warning or 0.7

        # Check if all metrics pass threshold
        all_pass = all(
            gate_metrics.get(name, 0) >= threshold
            for name, threshold in gate_thresholds.items()
        )

        gates.append(
            QualityGateResult(
                gate_name="ragas_quality",
                status=QualityGateStatus.PASSED if all_pass else QualityGateStatus.FAILED,
                metrics=gate_metrics,
                thresholds=gate_thresholds,
                message="RAGAS quality gate passed" if all_pass else "RAGAS quality gate failed",
            )
        )

        # Baseline pass rate gate
        baseline_pass_rate = metrics.get("baseline_pass_rate", 0)
        gate_threshold = 0.9  # 90% pass rate required

        gates.append(
            QualityGateResult(
                gate_name="baseline_pass_rate",
                status=(
                    QualityGateStatus.PASSED
                    if baseline_pass_rate >= gate_threshold
                    else QualityGateStatus.FAILED
                ),
                metrics={"baseline_pass_rate": baseline_pass_rate},
                thresholds={"baseline_pass_rate": gate_threshold},
                message=f"Baseline pass rate: {baseline_pass_rate:.2%}",
            )
        )

        # Overall score gate
        overall_score = metrics.get("overall_score", {})
        avg_score = overall_score.get("mean", 0)

        gates.append(
            QualityGateResult(
                gate_name="overall_score",
                status=(
                    QualityGateStatus.PASSED
                    if avg_score >= 0.7
                    else QualityGateStatus.WARNING
                ),
                metrics={"overall_score": avg_score},
                thresholds={"overall_score": 0.7},
                message=f"Overall score: {avg_score:.3f}",
            )
        )

        return gates

    def _detect_regressions(self, comparison: dict[str, Any]) -> bool:
        """Detect if any regressions occurred.

        Args:
            comparison: Comparison results from _compare_with_baseline

        Returns:
            True if regression detected
        """
        # Check for critical degradations
        critical_metrics = ["faithfulness", "answer_relevancy", "context_precision"]

        for degraded in comparison.get("degraded", []):
            if degraded["metric"] in critical_metrics:
                # More than 10% degradation is critical
                if degraded["diff_pct"] < -10:
                    logger.warning(
                        f"[CI/CD] Critical regression detected: {degraded['metric']} "
                        f"degraded by {abs(degraded['diff_pct']):.1f}%"
                    )
                    return True

        return False

    def _generate_recommendations(
        self,
        metrics: dict[str, Any],
        comparison: dict[str, Any],
        quality_gates: list[QualityGateResult],
    ) -> list[str]:
        """Generate improvement recommendations.

        Args:
            metrics: Aggregated metrics
            comparison: Baseline comparison
            quality_gates: Quality gate results

        Returns:
            List of recommendations
        """
        recommendations = []

        # Analyze degraded metrics
        for degraded in comparison.get("degraded", []):
            metric_name = degraded["metric"]
            diff_pct = degraded["diff_pct"]

            if metric_name == "faithfulness":
                recommendations.append(
                    f"Faithfulness degraded by {abs(diff_pct):.1f}% - "
                    "Consider improving context grounding or citation verification"
                )
            elif metric_name == "answer_relevancy":
                recommendations.append(
                    f"Answer relevancy degraded by {abs(diff_pct):.1f}% - "
                    "Review query understanding or retrieval strategy"
                )
            elif metric_name == "context_precision":
                recommendations.append(
                    f"Context precision degraded by {abs(diff_pct):.1f}% - "
                    "Improve retrieval or reranking"
                )

        # Analyze failed quality gates
        for gate in quality_gates:
            if gate.status == QualityGateStatus.FAILED:
                recommendations.append(
                    f"Quality gate '{gate.gate_name}' failed - {gate.message}"
                )

        # Add positive recommendations for improvements
        for improved in comparison.get("improved", []):
            metric_name = improved["metric"]
            diff_pct = improved["diff_pct"]
            recommendations.append(
                f"Good: {metric_name} improved by {diff_pct:.1f}% - keep these changes"
            )

        return recommendations

    def _determine_overall_status(
        self, quality_gates: list[QualityGateResult], regression_detected: bool
    ) -> QualityGateStatus:
        """Determine overall CI/CD status.

        Args:
            quality_gates: Quality gate results
            regression_detected: Whether regression detected

        Returns:
            Overall quality gate status
        """
        if regression_detected:
            return QualityGateStatus.FAILED

        failed_gates = [g for g in quality_gates if g.status == QualityGateStatus.FAILED]
        warning_gates = [g for g in quality_gates if g.status == QualityGateStatus.WARNING]

        if failed_gates:
            return QualityGateStatus.FAILED
        elif warning_gates:
            return QualityGateStatus.WARNING
        else:
            return QualityGateStatus.PASSED

    def _get_git_commit(self) -> str:
        """Get current git commit hash.

        Returns:
            Git commit hash
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Failed to get git commit: {e}")
            return "unknown"

    def _get_git_branch(self) -> str:
        """Get current git branch name.

        Returns:
            Git branch name
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Failed to get git branch: {e}")
            return "unknown"

    def save_result(self, result: CICDResult, filepath: str | Path) -> None:
        """Save CI/CD result to JSON file.

        Args:
            result: CI/CD result
            filepath: Path to save result
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved CI/CD result to {filepath}")

    def save_baseline(self, metrics: dict[str, Any], filepath: str | Path) -> None:
        """Save current metrics as new baseline.

        Args:
            metrics: Aggregated metrics
            filepath: Path to save baseline
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Extract baseline metrics
        baseline_metrics = {}

        ragas_metrics = metrics.get("ragas_metrics", {})
        for metric_name, metric_data in ragas_metrics.items():
            baseline_metrics[metric_name] = metric_data.get("mean", 0)

        baseline_data = {
            "created_at": datetime.utcnow().isoformat(),
            "metrics": baseline_metrics,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(baseline_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved baseline to {filepath}")


__all__ = [
    "CICDEvaluator",
    "CICDResult",
    "QualityGateResult",
    "QualityGateStatus",
]
