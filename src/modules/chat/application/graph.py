"""Application-level ChatGraph orchestration.

The graph owns workflow routing for chat requests:
classification is the first node, then dispatch chooses the appropriate
handler such as conversational chat or the RAG subflow.
"""

from typing import Any, AsyncIterator, TypedDict

from langgraph.graph import END, StateGraph
from loguru import logger

from src.modules.chat.application.dto import ChatQuery, StreamChunk
from src.shared.ports.classification import ClassificationResult, Intent
from src.shared.ports.handlers import HandlerResult, QueryHandlerBase


class ChatGraphState(TypedDict, total=False):
    """State passed between ChatGraph nodes."""

    query: ChatQuery
    context: dict[str, Any]
    classification: ClassificationResult
    handler_name: str
    handler_result: HandlerResult
    error: str


class ChatGraph:
    """LangGraph workflow for application-level chat routing."""

    def __init__(
        self,
        classifier: Any,
        handlers: dict[Intent, QueryHandlerBase],
        default_intent: Intent = Intent.RAG,
    ):
        """Initialize ChatGraph with classifier and handler registry."""
        self.classifier = classifier
        self.handlers = handlers
        self.default_intent = default_intent
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the application-level chat graph."""
        graph = StateGraph(ChatGraphState)
        graph.add_node("classify", self._classify_node)
        graph.add_node("dispatch", self._dispatch_node)
        graph.set_entry_point("classify")
        graph.add_edge("classify", "dispatch")
        graph.add_edge("dispatch", END)
        return graph.compile()

    async def run(self, query: ChatQuery) -> ChatGraphState:
        """Run the full non-streaming chat graph."""
        initial_state: ChatGraphState = {
            "query": query,
            "context": self._build_context(query),
        }
        return await self.graph.ainvoke(initial_state)

    async def run_stream(self, query: ChatQuery) -> AsyncIterator[dict[str, Any]]:
        """Run graph routing, then stream from the selected handler.

        The classification node remains the first workflow step. Handler streaming
        is delegated directly so the existing SSE chunk contract is preserved.
        """
        state: ChatGraphState = {
            "query": query,
            "context": self._build_context(query),
        }
        state.update(await self._classify_node(state))

        classification = state["classification"]
        handler = self._select_handler(classification)
        handler_name = self._get_handler_name(classification.intent)

        yield StreamChunk.routing(
            router_name=handler_name,
            intent=classification.intent.value,
            confidence=classification.confidence,
            reasoning=classification.reason,
        )

        async for chunk in handler.handle_stream(
            query=query.message,
            user_id=query.user_id,
            classification=classification,
            context=state.get("context") or None,
        ):
            yield chunk

    async def _classify_node(self, state: ChatGraphState) -> ChatGraphState:
        """Classify the query intent."""
        query = state["query"]
        logger.info("🔍 <cyan>[CHAT GRAPH: CLASSIFY]</cyan> Classifying query intent...")

        try:
            classification = await self.classifier.classify(
                query=query.message,
                user_id=str(query.user_id),
                context=state.get("context"),
            )
        except Exception as e:
            logger.warning(
                f"⚠️  <yellow>[CHAT GRAPH: CLASSIFY FALLBACK]</yellow> "
                f"Classification failed: {e}. Defaulting to {self.default_intent.value}."
            )
            classification = ClassificationResult(
                intent=self.default_intent,
                confidence=0.5,
                reason=f"Classification fallback: {e}",
            )

        logger.info(
            f"📊 <cyan>[CHAT GRAPH: CLASSIFY RESULT]</cyan> "
            f"Intent: <magenta>{classification.intent.value}</magenta>, "
            f"Confidence: <yellow>{classification.confidence:.2f}</yellow>, "
            f"Reason: {classification.reason}"
        )
        return {"classification": classification}

    async def _dispatch_node(self, state: ChatGraphState) -> ChatGraphState:
        """Dispatch the query to the handler selected by classification."""
        query = state["query"]
        classification = state["classification"]
        handler = self._select_handler(classification)
        handler_name = self._get_handler_name(classification.intent)

        logger.info(
            f"🎯 <magenta>[CHAT GRAPH: DISPATCH]</magenta> "
            f"Selected handler <yellow>{handler_name}</yellow> "
            f"for intent '<magenta>{classification.intent.value}</magenta>'"
        )

        result = await handler.handle(
            query=query.message,
            user_id=query.user_id,
            classification=classification,
            context=state.get("context") or None,
        )
        return {
            "handler_name": handler_name,
            "handler_result": result,
        }

    def _select_handler(self, classification: ClassificationResult) -> QueryHandlerBase:
        """Select handler by classified intent with a RAG fallback."""
        handler = self.handlers.get(classification.intent)
        if handler is None:
            handler = self.handlers.get(self.default_intent)
        if handler is None:
            raise ValueError(
                f"No handler registered for intent: {classification.intent}. "
                f"Available handlers: {list(self.handlers.keys())}"
            )
        return handler

    def _get_handler_name(self, intent: Intent) -> str:
        """Get a human-readable handler name."""
        handler = self.handlers.get(intent) or self.handlers.get(self.default_intent)
        if handler and hasattr(handler, "get_name"):
            return handler.get_name()
        return f"{intent.value}Handler"

    @staticmethod
    def _build_context(query: ChatQuery) -> dict[str, Any]:
        """Build handler context from query metadata."""
        context = dict(query.context or {})
        if query.conversation_history:
            context["conversation_history"] = query.conversation_history
        return context


__all__ = ["ChatGraph", "ChatGraphState"]
