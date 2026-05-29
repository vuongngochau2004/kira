"""LLM-based query intent classifier."""

from typing import Any

from src.agents.llm import chat_async
from src.agents.utils import parse_json_response
from src.agents.prompts import ROUTING_CLASSIFIER_PROMPT


# Intent types that routers can handle
class Intent:
    """Intent types for query classification.

    Current intents:
    - CONVERSATIONAL: Greetings, casual chat
    - RAG: Questions requiring document knowledge

    Future intents:
    - DRAFTING: Legal document drafting (to be added)
    """
    CONVERSATIONAL = "conversational"
    RAG = "rag"
    # Reserved for future use
    # DRAFTING = "drafting"


class QueryClassification:
    """Result of query classification."""

    def __init__(
        self,
        intent: str,
        confidence: float,
        reason: str = "",
    ):
        """Initialize classification result.

        Args:
            intent: Classified intent type
            confidence: Confidence score 0.0-1.0
            reason: Explanation for classification
        """
        self.intent = intent
        self.confidence = confidence
        self.reason = reason

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "reason": self.reason,
        }

    def __repr__(self) -> str:
        return f"QueryClassification(intent={self.intent}, confidence={self.confidence})"


class QueryClassifier:
    """LLM-based query intent classifier.

    Designed for easy extension - add new intents when adding new agents.
    """

    def __init__(self, temperature: float = 0.1, max_tokens: int = 100):
        """Initialize classifier.

        Args:
            temperature: Low temperature for consistent classification
            max_tokens: Max tokens in response
        """
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def classify(self, query: str) -> QueryClassification:
        """Classify query intent using LLM.

        Args:
            query: User query

        Returns:
            QueryClassification with intent and confidence
        """
        prompt = ROUTING_CLASSIFIER_PROMPT.format(query=query)

        try:
            response = await chat_async(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            parsed = parse_json_response(response["content"])

            if not parsed:
                # Fallback to RAG if parsing fails (safer default)
                return QueryClassification(
                    intent=Intent.RAG,
                    confidence=0.5,
                    reason="JSON parsing failed, using default RAG",
                )

            return QueryClassification(
                intent=parsed.get("intent", Intent.RAG),
                confidence=float(parsed.get("confidence", 0.5)),
                reason=parsed.get("reason", ""),
            )

        except Exception as e:
            # Fallback on error
            return QueryClassification(
                intent=Intent.RAG,
                confidence=0.3,
                reason=f"Classification error: {str(e)}",
            )


# Router intent mapping
# Easy to extend when adding new agents
INTENT_TO_ROUTER = {
    Intent.CONVERSATIONAL: "ConversationalRouter",
    Intent.RAG: "RAGRouter",
    # Future: Intent.DRAFTING: "DraftingRouter",
}


__all__ = [
    "Intent",
    "QueryClassification",
    "QueryClassifier",
    "INTENT_TO_ROUTER",
]
