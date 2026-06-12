"""
Interface definitions for dependency injection container using Abstract Base Classes (ABC).

This module provides ABC-based container interfaces for stricter interface compliance
with @abstractmethod decorators.

Key differences from Protocol:
- Uses @abstractmethod for enforced implementation
- Requires explicit inheritance (nominal subtyping)
- Better for production code enforcement

This module now contains BOTH ports AND data models (Lifecycle, ServiceDescriptor).
Previously, data models were in src.protocols.container - now unified in ABC-only architecture.

Example:
    >>> from src.shared.ports.container import ScopeManagerBase
    >>>
    >>> class RequestScopeManager(ScopeManagerBase):
    ...     def __init__(self):
    ...         self._scopes: dict[str, dict[Type, Any]] = {}
    ...
    ...     async def create_scope(self, scope_id: str) -> None:
    ...         self._scopes[scope_id] = {}
    ...
    ...     async def get_scoped_service(self, interface: Type[T], scope_id: str, container) -> T:
    ...         if scope_id not in self._scopes:
    ...             raise ValueError(f"Scope {scope_id} not created")
    ...         if interface not in self._scopes[scope_id]:
    ...             self._scopes[scope_id][interface] = await container.get(interface)
    ...         return self._scopes[scope_id][interface]
    ...
    ...     async def dispose_scope(self, scope_id: str) -> None:
    ...         if scope_id in self._scopes:
    ...             del self._scopes[scope_id]
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import TypeVar, Type, Any, Callable, Awaitable
from dataclasses import dataclass

T = TypeVar("T")


__all__ = [
    # Data models
    "Lifecycle",
    "ServiceDescriptor",
    # ports
    "DependencyContainerBase",
    "ServiceRegistryBase",
    "ScopeManagerBase",
]


# ============================================================================
# DATA MODELS (formerly in src.protocols.container)
# ============================================================================

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


# ============================================================================
# ABC INTERFACES
# ============================================================================

class DependencyContainerBase(ABC):
    """
    Base class for dependency injection container.

    Enforces implementation of all DI container methods using @abstractmethod.
    Defines the interface contract that all DI container implementations must follow.

    Example:
        >>> class ServiceContainer(DependencyContainerBase):
        ...     def __init__(self):
        ...         self._services: dict[Type, ServiceDescriptor] = {}
        ...         self._singletons: dict[Type, Any] = {}
        ...
        ...     async def register_singleton(self, interface: Type[T], implementation: Type[T] | T) -> None:
        ...         self._services[interface] = ServiceDescriptor(interface, implementation, Lifecycle.SINGLETON)
        ...
        ...     # Must implement all abstract methods
    """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
            >>> def create_classifier(container: DependencyContainerBase) -> ClassificationStrategy:
            ...     retriever = await container.get(Retriever)
            ...     llm = await container.get(LLMClient)
            ...     return CompositeClassifier(retriever, llm)
            ...
            >>> await container.register_factory(ClassificationStrategy, create_classifier)
        """
        ...

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
            ...         print(handler.get_name())
        """
        ...

    @abstractmethod
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

    @abstractmethod
    async def clear_scope(self, scope_id: str) -> None:
        """
        Clear scoped services for a scope.

        Args:
            scope_id: Scope identifier to clear

        Example:
            >>> await container.clear_scope("request_123")
        """
        ...


class ServiceRegistryBase(ABC):
    """
    Base class for service registration and container initialization.

    Defines the interface contract for service registry implementations.
    Enforces implementation using @abstractmethod.

    Example:
        >>> class MyServiceRegistry(ServiceRegistryBase):
        ...     @staticmethod
        ...     async def initialize_container() -> DependencyContainerBase:
        ...         container = ServiceContainer()
        ...         await container.register_singleton(ClassificationStrategy, CompositeClassifier)
        ...         await container.register_singleton(QueryHandler, RAGHandler)
        ...         return container
        ...
        ...     async def warm_up(self, container: DependencyContainerBase) -> None:
        ...         # Pre-instantiate critical services
        ...         pass
    """

    @staticmethod
    @abstractmethod
    async def initialize_container() -> "DependencyContainerBase":
        """
        Initialize DI container with all services.

        Returns:
            Initialized dependency container

        Example:
            >>> container = await ServiceRegistryBase.initialize_container()
            >>> classifier = await container.get(ClassificationStrategy)
        """
        ...

    @abstractmethod
    async def warm_up(self, container: "DependencyContainerBase") -> None:
        """
        Warm up container by pre-instantiating critical services.

        Args:
            container: DI container to warm up

        Example:
            >>> await registry.warm_up(container)
        """
        ...


class ScopeManagerBase(ABC):
    """
    Base class for managing scoped services.

    Defines the interface contract for scope manager implementations.
    Enforces strict implementation with @abstractmethod decorators.

    Example:
        >>> class RequestScopeManager(ScopeManagerBase):
        ...     def __init__(self):
        ...         self._scopes: dict[str, dict[Type, Any]] = {}
        ...
        ...     async def create_scope(self, scope_id: str) -> None:
        ...         self._scopes[scope_id] = {}
        ...
        ...     async def get_scoped_service(self, interface: Type[T], scope_id: str, container) -> T:
        ...         if scope_id not in self._scopes:
        ...             raise ValueError(f"Scope {scope_id} not created")
        ...         if interface not in self._scopes[scope_id]:
        ...             self._scopes[scope_id][interface] = await container.get(interface)
        ...         return self._scopes[scope_id][interface]
        ...
        ...     async def dispose_scope(self, scope_id: str) -> None:
        ...         if scope_id in self._scopes:
        ...             del self._scopes[scope_id]
    """

    @abstractmethod
    async def create_scope(self, scope_id: str) -> None:
        """
        Create a new scope.

        Args:
            scope_id: Scope identifier

        Example:
            >>> await scope_manager.create_scope("request_123")
        """
        ...

    @abstractmethod
    async def get_scoped_service(
        self,
        interface: Type[T],
        scope_id: str,
        container: "DependencyContainerBase"
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

    @abstractmethod
    async def dispose_scope(self, scope_id: str) -> None:
        """
        Dispose scoped services.

        Args:
            scope_id: Scope identifier to dispose

        Example:
            >>> await scope_manager.dispose_scope("request_123")
        """
        ...
