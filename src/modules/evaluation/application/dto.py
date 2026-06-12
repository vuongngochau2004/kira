"""
Data Transfer Objects (DTOs) for evaluation use case.

Defines request/response models for evaluation operations.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class EvaluationQuery:
    """
    Evaluation request DTO.

    Attributes:
        query: User query
        context: Retrieved context
        answer: Generated answer
        ground_truth: Ground truth answer (optional)
    """

    query: str
    context: str
    answer: str
    ground_truth: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "query": self.query,
            "context": self.context,
            "answer": self.answer,
            "ground_truth": self.ground_truth
        }


@dataclass
class EvaluationResultDTO:
    """
    Evaluation result response DTO.

    Attributes:
        faithfulness: Faithfulness score (0-1)
        answer_relevancy: Answer relevancy score (0-1)
        context_precision: Context precision score (0-1)
        context_recall: Context recall score (0-1)
        metadata: Additional metadata
    """

    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    metadata: dict[str, Any]

    @classmethod
    def from_metrics(cls, metrics: dict[str, float]) -> "EvaluationResultDTO":
        """Create DTO from metrics dict."""
        return cls(
            faithfulness=metrics.get("faithfulness", 0.0),
            answer_relevancy=metrics.get("answer_relevancy", 0.0),
            context_precision=metrics.get("context_precision", 0.0),
            context_recall=metrics.get("context_recall", 0.0),
            metadata={}
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "faithfulness": self.faithfulness,
            "answer_relevancy": self.answer_relevancy,
            "context_precision": self.context_precision,
            "context_recall": self.context_recall,
            "metadata": self.metadata
        }

    def get_average_score(self) -> float:
        """Get average of all scores."""
        scores = [
            self.faithfulness,
            self.answer_relevancy,
            self.context_precision,
            self.context_recall
        ]
        return sum(scores) / len(scores) if scores else 0.0
