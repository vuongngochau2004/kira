"""
Service registry and container initialization.

Registers and configures all services for the DI container.
"""

from typing import Optional

from src.shared.kernel.di.container import ServiceContainer
from src.shared.ports.classification import ClassificationStrategyBase
from src.shared.ports.handlers import QueryHandlerBase


# Global container instance
_container: Optional[ServiceContainer] = None


class ServiceRegistry:
    """
    Service registration and container initialization.

    Registers all application services with appropriate lifecycles:
    - SINGLETON: Shared stateless services (classifiers, handlers)
    - TRANSIENT: Stateful services (request-scoped objects)
    - FACTORY: Complex instantiation logic

    Example:
        >>> registry = ServiceRegistry()
        >>> container = await registry.initialize_container()
        >>> classifier = await container.get(ClassificationStrategy)
    """

    @staticmethod
    async def initialize_container() -> ServiceContainer:
        """
        Initialize DI container with all services.

        Registers:
        - Classification strategies (CompositeClassifier with Keyword + LLM)
        - Query handlers (RAGHandler, ConversationalHandler)
        - Supporting services (LLM clients, retrievers, etc.)

        Returns:
            Initialized dependency container

        Example:
            >>> container = await ServiceRegistry.initialize_container()
            >>> classifier = await container.get(ClassificationStrategy)
        """
        container = ServiceContainer()

        # Import services here to avoid circular imports
        # Classification strategies
        try:
            from src.modules.classification.domain.strategies.composite import CompositeClassifier
            from src.modules.classification.domain.strategies.keyword import KeywordStrategy
            from src.modules.classification.domain.strategies.llm import LLMStrategy
            from src.modules.classification.domain.strategies.cached import CachedStrategy

            # Register classification chain
            # Keyword -> Cached LLM with fallback
            keyword_strategy = KeywordStrategy()
            llm_strategy = LLMStrategy()
            cached_llm = CachedStrategy(llm_strategy, cache_size=1000, ttl=3600)

            classifier = CompositeClassifier(
                strategies=[keyword_strategy, cached_llm],
                thresholds={"keyword": 0.7, "cached": 0.6, "llm": 0.5}
            )

            await container.register_singleton(ClassificationStrategyBase, classifier)

        except ImportError as e:
            # Fallback if classification module not available
            print(f"Warning: Could not import classification strategies: {e}")

        # Query handlers
        try:
            from src.modules.chat.infrastructure.handlers.rag_handler import RAGHandler
            from src.modules.chat.infrastructure.handlers.conversational import ConversationalHandler

            # Register handlers as singletons (stateless) under concrete classes
            await container.register_singleton(RAGHandler, RAGHandler())
            await container.register_singleton(ConversationalHandler, ConversationalHandler())

        except ImportError as e:
            print(f"Warning: Could not import handlers: {e}")

        # Hexagonal Ports & Adapters wiring
        try:
            from src.shared.ports.llm import LLMPort
            from src.shared.ports.vector_store import VectorStorePort
            from src.shared.ports.embedding import EmbeddingPort
            from src.shared.ports.storage import StoragePort
            from src.shared.ports.keyword_index import KeywordIndexPort
            from src.shared.ports.ocr import OCRPort

            from src.shared.adapters.llm.glm_adapter import GLMAdapter
            from src.shared.adapters.vector.qdrant_adapter import QdrantAdapter
            from src.shared.adapters.embedding.api_adapter import EmbeddingAPIAdapter
            from src.shared.adapters.storage.minio_adapter import MinIOAdapter
            from src.shared.adapters.ocr.paddleocr_adapter import PaddleOCRAdapter
            from src.modules.retrieval.infrastructure.keyword.bm25_adapter import BM25KeywordIndexAdapter
            from src.modules.retrieval.infrastructure.keyword.bm25_manager import get_bm25_manager

            await container.register_singleton(LLMPort, GLMAdapter())
            await container.register_singleton(VectorStorePort, QdrantAdapter())
            await container.register_singleton(EmbeddingPort, EmbeddingAPIAdapter())
            await container.register_singleton(StoragePort, MinIOAdapter())
            await container.register_singleton(
                KeywordIndexPort,
                BM25KeywordIndexAdapter(manager=get_bm25_manager()),
            )
            await container.register_singleton(OCRPort, PaddleOCRAdapter())

        except ImportError as e:
            print(f"Warning: Could not import Hexagonal Ports/Adapters: {e}")

        return container

    async def warm_up(self, container: ServiceContainer) -> None:
        """
        Warm up container by pre-instantiating critical services.

        Pre-instantiates expensive services to avoid first-request latency.

        Args:
            container: DI container to warm up

        Example:
            >>> registry = ServiceRegistry()
            >>> container = await registry.initialize_container()
            >>> await registry.warm_up(container)
        """
        # Warm up classification strategy (likely to be used immediately)
        try:
            await container.get(ClassificationStrategyBase)
        except Exception as e:
            print(f"Warning: Failed to warm up ClassificationStrategyBase: {e}")

        # Warm up handlers
        try:
            from src.modules.chat.infrastructure.handlers.rag_handler import RAGHandler
            from src.modules.chat.infrastructure.handlers.conversational import ConversationalHandler
            await container.get(RAGHandler)
            await container.get(ConversationalHandler)
        except Exception as e:
            print(f"Warning: Failed to warm up handlers: {e}")


async def get_container() -> ServiceContainer:
    """
    Get global DI container (lazy initialization).

    Creates container on first call, returns cached instance on subsequent calls.

    Returns:
        Global DI container instance

    Example:
        >>> container = await get_container()
        >>> service = await container.get(MyService)
    """
    global _container

    if _container is None:
        _container = await ServiceRegistry.initialize_container()

    return _container


def reset_container() -> None:
    """
    Reset global container.

    Clears the cached container instance. Useful for testing.

    Example:
        >>> reset_container()
        >>> container = await get_container()  # Fresh instance
    """
    global _container
    _container = None


async def reload_container() -> ServiceContainer:
    """
    Reload global container (reinitialize all services).

    Clears existing container and creates fresh instance.

    Returns:
        Newly initialized container

    Example:
        >>> container = await reload_container()
    """
    global _container

    # Dispose old container if exists
    if _container is not None:
        await _container.dispose()

    # Create new container
    _container = await ServiceRegistry.initialize_container()

    return _container
