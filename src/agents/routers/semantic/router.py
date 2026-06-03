"""Semantic router implementation for KIRA."""

import logging
from typing import Optional, List, Any

from semantic_router import SemanticRouter
from semantic_router.encoders import DenseEncoder

from src.ingestion.embedding import embed_single


logger = logging.getLogger(__name__)


class CustomEmbeddingEncoder(DenseEncoder):
    """Custom encoder using KIRA's embedding service."""

    def __init__(self):
        """Initialize custom encoder."""
        super().__init__(name="kira-embedding")

    def __call__(self, texts: List[str]) -> List[List[float]]:
        """Encode texts to embeddings.

        Args:
            texts: List of texts to encode

        Returns:
            List of embedding vectors
        """
        return [embed_single(text) for text in texts]


class KIRASemanticRouter:
    """KIRA semantic router wrapper."""

    def __init__(self, threshold: float = 0.75):
        """Initialize semantic router.

        Args:
            threshold: Similarity threshold for routing (0.0-1.0)
        """
        self.threshold = threshold

        # Initialize semantic router
        self._router: Optional[SemanticRouter] = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize the semantic router with routes."""
        from .routes import get_all_routes

        routes = get_all_routes()

        # Map route names to KIRA router names
        self.route_name_mapping = {
            "conversational": "ConversationalRouter",
            "rag_legal": "RAGRouter",
        }

        # Create semantic router with custom encoder
        self._router = SemanticRouter(
            encoder=CustomEmbeddingEncoder(),
        )

        # Add routes to the router
        try:
            for route in routes:
                self._router.add(route)
            logger.info(f"Semantic router initialized with {len(routes)} routes")
        except Exception as e:
            logger.error(f"Failed to add routes to semantic router: {e}")
            raise

    def route(self, query: str) -> Optional[dict]:
        """Route query to appropriate router.

        Args:
            query: User query

        Returns:
            Routing decision dict or None if below threshold
        """
        if self._router is None:
            return None

        result = self._router(query)

        if result is None:
            return None

        # SemanticRouter returns a single RouteChoice object (not a list)
        route_choice = result

        # RouteChoice has 'name' and 'similarity_score' attributes
        try:
            route_name = route_choice.name
            score = route_choice.similarity_score
        except AttributeError:
            # Fallback for different API versions
            route_name = getattr(route_choice, 'name', '')
            score = getattr(route_choice, 'similarity_score', getattr(route_choice, 'score', 0.0))

        # Apply threshold filtering (not done by SemanticRouter)
        if score < self.threshold:
            logger.debug(
                f"Query '{query[:30]}...' score {score:.2f} below threshold {self.threshold}"
            )
            return None

        # Get router name from mapping, log warning if unknown
        if route_name not in self.route_name_mapping:
            logger.warning(
                f"Unknown semantic route '{route_name}', defaulting to RAGRouter"
            )

        return {
            "router_name": self.route_name_mapping.get(
                route_name,
                "RAGRouter"  # Default fallback
            ),
            "semantic_route": route_name,
            "score": score,
            "method": "semantic",
        }

    async def route_async(self, query: str) -> Optional[dict]:
        """Async version of route method.

        Args:
            query: User query

        Returns:
            Routing decision dict or None
        """
        return self.route(query)  # Semantic router is synchronous


__all__ = ["KIRASemanticRouter"]
