"""
Service registry and container initialization.

Registers and configures all services for the DI container.
"""

from typing import Optional

from kira.chat.intent.base import ClassificationStrategyBase
from kira.config import settings
from kira.di.container import ServiceContainer

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
            from kira.chat.intent.cached import CachedStrategy
            from kira.chat.intent.composite import CompositeClassifier
            from kira.chat.intent.keyword import KeywordStrategy
            from kira.chat.intent.llm import LLMStrategy

            # Register classification chain
            # Keyword -> Cached LLM with fallback
            keyword_strategy = KeywordStrategy()
            llm_strategy = LLMStrategy()
            cached_llm = CachedStrategy(llm_strategy, cache_size=1000, ttl=3600)

            strategies: list[ClassificationStrategyBase] = [keyword_strategy, cached_llm]
            if settings.legal_enabled:
                from kira.chat.intent.legal import (
                    LegalKeywordStrategy,
                )
                from kira.legal.extraction.rules import DOCUMENT_NUMBER_PATTERN

                # Legal corpus cues must win over the broad file keywords ("điều", "về", ...).
                strategies.insert(
                    0,
                    LegalKeywordStrategy(settings.legal_routing_keywords, DOCUMENT_NUMBER_PATTERN),
                )
            classifier = CompositeClassifier(
                strategies=strategies,
                thresholds={"keyword": 0.7, "cached": 0.6, "llm": 0.5},
            )

            await container.register_singleton(ClassificationStrategyBase, classifier)

        except ImportError as e:
            # Fallback if classification module not available
            print(f"Warning: Could not import classification strategies: {e}")

        # Hexagonal Ports & Adapters wiring
        try:
            from kira.providers.embedding.base import EmbeddingPort
            from kira.providers.embedding.factory import create_embedding_adapter
            from kira.providers.llm.adapter import GLMAdapter
            from kira.providers.llm.base import LLMPort
            from kira.providers.ocr.adapter import PaddleOCRAdapter
            from kira.providers.ocr.base import OCRPort
            from kira.providers.storage.base import StoragePort
            from kira.providers.storage.minio import MinIOAdapter
            from kira.providers.vector.base import VectorStorePort
            from kira.providers.vector.qdrant import QdrantAdapter
            from kira.retrieval.bm25_adapter import (
                BM25KeywordIndexAdapter,
            )
            from kira.retrieval.bm25_manager import get_bm25_manager
            from kira.retrieval.keyword_port import KeywordIndexPort

            await container.register_singleton(LLMPort, GLMAdapter())
            await container.register_singleton(VectorStorePort, QdrantAdapter())
            await container.register_singleton(EmbeddingPort, create_embedding_adapter())
            await container.register_singleton(StoragePort, MinIOAdapter())
            await container.register_singleton(
                KeywordIndexPort,
                BM25KeywordIndexAdapter(manager=get_bm25_manager()),
            )
            await container.register_singleton(OCRPort, PaddleOCRAdapter())

        except ImportError as e:
            print(f"Warning: Could not import Hexagonal Ports/Adapters: {e}")

        # Query handlers are composed only after their ports are available.
        try:
            from kira.chat.handlers.conversational import (
                ConversationalHandler,
            )
            from kira.chat.handlers.drafting import (
                AdministrativeDraftingHandler,
            )
            from kira.chat.handlers.rag import RAGHandler
            from kira.chat.rag.composition import create_default_rag_pipeline_service
            from kira.providers.embedding.base import EmbeddingPort
            from kira.providers.llm.base import LLMPort
            from kira.providers.storage.base import StoragePort
            from kira.retrieval.composition import create_search_use_case

            llm = await container.get(LLMPort)
            embedding = await container.get(EmbeddingPort)
            storage = await container.get(StoragePort)
            await container.register_singleton(
                RAGHandler,
                RAGHandler(
                    rag_service=create_default_rag_pipeline_service(
                        embedding=embedding,
                        search=create_search_use_case(llm_client=llm),
                        llm=llm,
                    )
                ),
            )
            await container.register_singleton(
                ConversationalHandler, ConversationalHandler(llm=llm)
            )
            await container.register_singleton(
                AdministrativeDraftingHandler,
                AdministrativeDraftingHandler(
                    embedding=embedding,
                    search=create_search_use_case(llm_client=llm),
                    llm=llm,
                    storage=storage,
                ),
            )
            if settings.legal_enabled:
                from kira.legal.chat_handler import LegalQAHandler
                from kira.legal.composition import create_legal_qa_handler

                await container.register_singleton(
                    LegalQAHandler, create_legal_qa_handler(llm=llm, embedding=embedding)
                )
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
            from kira.chat.handlers.conversational import (
                ConversationalHandler,
            )
            from kira.chat.handlers.drafting import (
                AdministrativeDraftingHandler,
            )
            from kira.chat.handlers.rag import RAGHandler

            await container.get(RAGHandler)
            await container.get(ConversationalHandler)
            await container.get(AdministrativeDraftingHandler)
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
