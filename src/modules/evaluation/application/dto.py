"""DTOs for evaluation use cases."""

from dataclasses import dataclass
from typing import Any


@dataclass
class EvaluationQuery:
    """One generated RAG output to evaluate."""

    query: str
    context: str
    answer: str
    expected_answer: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "context": self.context,
            "answer": self.answer,
            "expected_answer": self.expected_answer,
        }


@dataclass
class EvaluationResultDTO:
    """Compact metric view for UI/application callers."""

    scores: dict[str, float]
    overall_score: float
    passed: bool
    metadata: dict[str, Any]

    @classmethod
    def from_metrics(cls, metrics: dict[str, float]) -> "EvaluationResultDTO":
        overall = sum(metrics.values()) / len(metrics) if metrics else 0.0
        return cls(scores=metrics, overall_score=overall, passed=overall >= 0.7, metadata={})

    def to_dict(self) -> dict[str, Any]:
        return {
            "scores": self.scores,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "metadata": self.metadata,
        }
