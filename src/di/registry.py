"""
Service registry and container initialization.

Registers and configures all services for the DI container.
"""

from typing import Optional

from src.di.container import ServiceContainer
from src.interfaces.classification import ClassificationStrategyBase
from src.interfaces.handlers import QueryHandlerBase


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
            from src.classification.strategies.composite import CompositeClassifier
            from src.classification.strategies.keyword import KeywordStrategy
            from src.classification.strategies.llm import LLMStrategy
            from src.classification.strategies.cached import CachedStrategy

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
            from src.handlers.rag import RAGHandler
            from src.handlers.conversational import ConversationalHandler

            # Register handlers as singletons (stateless)
            await container.register_singleton(QueryHandlerBase, RAGHandler())
            await container.register_singleton(QueryHandlerBase, ConversationalHandler())

        except ImportError as e:
            print(f"Warning: Could not import handlers: {e}")

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
            # Get all handler implementations
            handlers = await container.get_all(QueryHandlerBase)
            for handler in handlers:
                pass  # Handler already instantiated
        except Exception as e:
            print(f"Warning: Failed to warm up QueryHandlerBase: {e}")


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
