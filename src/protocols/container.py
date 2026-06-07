"""
Dependency injection container protocols.

This module defines Protocol-based interfaces for the DI container,
enabling protocol-based dependency injection following the DIP principle.

Service Lifecycle:
- Singleton: One instance for app lifetime
- Transient: New instance each time
- Scoped: One instance per scope (e.g., per request)

Example:
    >>> from src.protocols.container import DependencyContainer, ServiceRegistry
    >>>
    >>> container = DependencyContainer()
    >>> container.register_singleton(MyProtocol, MyImplementation)
    >>> instance = await container.get(MyProtocol)
"""

from typing import Protocol, TypeVar, Type, Any, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum


T = TypeVar("T")


class Lifecycle(str, Enum):
    """
    Service lifecycle enumeration.

    - SINGLETON: One instance for app lifetime
    - TRANSIENT: New instance each time
    - SCOPED: One instance per scope (e.g., per request)
    """

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


@dataclass
class ServiceDescriptor:
    """
    Service registration descriptor.

    Attributes:
        interface: Protocol/interface type
        implementation: Concrete implementation type or instance
        lifecycle: Service lifecycle (singleton, transient, scoped)
        factory: Optional factory function for custom instantiation
        dependencies: List of required service types
        metadata: Additional metadata

    Example:
        >>> descriptor = ServiceDescriptor(
        ...     interface=ClassificationStrategy,
        ...     implementation=CompositeClassifier,
        ...     lifecycle=Lifecycle.SINGLETON,
        ...     dependencies=[Retriever, LLMClient]
        ... )
    """

    interface: Type
    implementation: Type | Any
    lifecycle: Lifecycle = Lifecycle.SINGLETON
    factory: Callable[..., Any] | Callable[..., Awaitable[Any]] | None = None
    dependencies: list[Type] | None = None
    metadata: dict[str, Any] | None = None

    def is_singleton(self) -> bool:
        """Check if service is singleton."""
        return self.lifecycle == Lifecycle.SINGLETON

    def is_transient(self) -> bool:
        """Check if service is transient."""
        return self.lifecycle == Lifecycle.TRANSIENT

    def is_scoped(self) -> bool:
        """Check if service is scoped."""
        return self.lifecycle == Lifecycle.SCOPED


class DependencyContainer(Protocol):
    """
    Protocol for dependency injection container.

    Enables protocol-based dependency injection following the DIP principle.

    Example:
        >>> class ServiceContainer:
        ...     def __init__(self):
        ...         self._services: dict[Type, ServiceDescriptor] = {}
        ...         self._singletons: dict[Type, Any] = {}
        ...
        ...     async def register_singleton(self, interface: Type[T], implementation: Type[T] | T) -> None:
        ...         self._services[interface] = ServiceDescriptor(interface, implementation, Lifecycle.SINGLETON)
        ...
        ...     async def get(self, interface: Type[T]) -> T:
        ...         descriptor = self._services.get(interface)
        ...         if descriptor.is_singleton():
        ...             if interface not in self._singletons:
        ...                 self._singletons[interface] = descriptor.implementation()
        ...             return self._singletons[interface]
        ...         return descriptor.implementation()
    """

    async def register_singleton(
        self,
        interface: Type[T],
        implementation: Type[T] | T
    ) -> None:
        """
        Register singleton service (one instance for app lifetime).

        Args:
            interface: Protocol/interface type
            implementation: Concrete implementation type or instance

        Example:
            >>> await container.register_singleton(ClassificationStrategy, CompositeClassifier)
        """
        ...

    async def register_transient(
        self,
        interface: Type[T],
        implementation: Type[T]
    ) -> None:
        """
        Register transient service (new instance each time).

        Args:
            interface: Protocol/interface type
            implementation: Concrete implementation type

        Example:
            >>> await container.register_transient(QueryHandler, RAGHandler)
        """
        ...

    async def register_scoped(
        self,
        interface: Type[T],
        implementation: Type[T],
        scope_id: str | None = None
    ) -> None:
        """
        Register scoped service (one instance per scope).

        Args:
            interface: Protocol/interface type
            implementation: Concrete implementation type
            scope_id: Optional scope identifier (e.g., request_id)

        Example:
            >>> await container.register_scoped(QueryHandler, RAGHandler, scope_id="request_123")
        """
        ...

    async def register_factory(
        self,
        interface: Type[T],
        factory: Callable[..., T] | Callable[..., Awaitable[T]]
    ) -> None:
        """
        Register factory function for custom instantiation.

        Args:
            interface: Protocol/interface type
            factory: Factory function (sync or async)

        Example:
            >>> def create_classifier(container: DependencyContainer) -> ClassificationStrategy:
            ...     retriever = await container.get(Retriever)
            ...     llm = await container.get(LLMClient)
            ...     return CompositeClassifier(retriever, llm)
            ...
            >>> await container.register_factory(ClassificationStrategy, create_classifier)
        """
        ...

    async def get(self, interface: Type[T]) -> T:
        """
        Resolve dependency by protocol.

        Args:
            interface: Protocol/interface type

        Returns:
            Service instance

        Raises:
            ValueError: If service not registered
            Exception: If instantiation fails

        Example:
            >>> classifier = await container.get(ClassificationStrategy)
            >>> result = await classifier.classify("query", "user123")
        """
        ...

    def get_sync(self, interface: Type[T]) -> T | None:
        """
        Synchronous get for non-async contexts.

        Returns None if service not instantiated yet.

        Args:
            interface: Protocol/interface type

        Returns:
            Service instance or None

        Example:
            >>> classifier = container.get_sync(ClassificationStrategy)
            >>> if classifier:
            ...     # Use cached singleton
            ...     pass
        """
        ...

    async def is_registered(self, interface: Type) -> bool:
        """
        Check if service is registered.

        Args:
            interface: Protocol/interface type

        Returns:
            True if registered, False otherwise

        Example:
            >>> if await container.is_registered(ClassificationStrategy):
            ...     classifier = await container.get(ClassificationStrategy)
        """
        ...

    async def get_all(self, interface: Type[T]) -> list[T]:
        """
        Get all registered implementations for interface.

        Useful for multiple implementations of same protocol.

        Args:
            interface: Protocol/interface type

        Returns:
            List of service instances

        Example:
            >>> handlers = await container.get_all(QueryHandler)
            >>> for handler in handlers:
            ...     print(handler.get_name())
        """
        ...

    def get_stats(self) -> dict[str, Any]:
        """
        Get container statistics.

        Returns:
            Dict with stats: registered_services, singleton_count, etc.

        Example:
            >>> stats = container.get_stats()
            >>> print(f"Registered services: {stats['registered_services']}")
        """
        ...

    async def clear_scope(self, scope_id: str) -> None:
        """
        Clear scoped services for a scope.

        Args:
            scope_id: Scope identifier to clear

        Example:
            >>> await container.clear_scope("request_123")
        """
        ...


class ServiceRegistry(Protocol):
    """
    Protocol for service registration and container initialization.

    Example:
        >>> class MyServiceRegistry:
        ...     @staticmethod
        ...     async def initialize_container() -> DependencyContainer:
        ...         container = ServiceContainer()
        ...         await container.register_singleton(ClassificationStrategy, CompositeClassifier)
        ...         await container.register_singleton(QueryHandler, RAGHandler)
        ...         return container
    """

    @staticmethod
    async def initialize_container() -> DependencyContainer:
        """
        Initialize DI container with all services.

        Returns:
            Initialized dependency container

        Example:
            >>> container = await ServiceRegistry.initialize_container()
            >>> classifier = await container.get(ClassificationStrategy)
        """
        ...

    async def warm_up(self, container: DependencyContainer) -> None:
        """
        Warm up container by pre-instantiating critical services.

        Args:
            container: DI container to warm up

        Example:
            >>> await registry.warm_up(container)
        """
        ...


class ScopeManager(Protocol):
    """
    Protocol for managing scoped services.

    Example:
        >>> class RequestScopeManager:
        ...     def __init__(self, request_id: str):
        ...         self.request_id = request_id
        ...         self._scoped_services: dict[Type, Any] = {}
        ...
        ...     async def get(self, interface: Type[T], container: DependencyContainer) -> T:
        ...         if interface not in self._scoped_services:
        ...             self._scoped_services[interface] = await container.get(interface)
        ...         return self._scoped_services[interface]
    """

    async def create_scope(self, scope_id: str) -> None:
        """
        Create a new scope.

        Args:
            scope_id: Scope identifier

        Example:
            >>> await scope_manager.create_scope("request_123")
        """
        ...

    async def get_scoped_service(
        self,
        interface: Type[T],
        scope_id: str,
        container: DependencyContainer
    ) -> T:
        """
        Get service within scope.

        Args:
            interface: Protocol/interface type
            scope_id: Scope identifier
            container: DI container

        Returns:
            Service instance (scoped)

        Example:
            >>> handler = await scope_manager.get_scoped_service(QueryHandler, "request_123", container)
        """
        ...

    async def dispose_scope(self, scope_id: str) -> None:
        """
        Dispose scoped services.

        Args:
            scope_id: Scope identifier to dispose

        Example:
            >>> await scope_manager.dispose_scope("request_123")
        """
        ...
