"""
Dependency injection container implementation.

Protocol-based DI container following SOLID principles.
"""

import asyncio
from typing import Type, TypeVar, Any, Callable, Awaitable, Optional
from threading import Lock

from src.shared.kernel.interfaces.container import Lifecycle, DependencyContainerBase, ServiceDescriptor


T = TypeVar("T")


class ServiceContainer(DependencyContainerBase):
    """
    Async-safe dependency injection container with protocol-based registration.

    Supports three lifecycles:
    - SINGLETON: One instance for app lifetime
    - TRANSIENT: New instance each time
    - SCOPED: One instance per scope (e.g., per request)

    Thread-safe for concurrent access.

    Example:
        >>> container = ServiceContainer()
        >>> await container.register_singleton(MyProtocol, MyImplementation)
        >>> instance = await container.get(MyProtocol)
    """

    def __init__(self):
        """Initialize empty DI container."""
        self._services: dict[Type, ServiceDescriptor] = {}
        self._singletons: dict[Type, Any] = {}
        self._scoped: dict[str, dict[Type, Any]] = {}
        self._lock = Lock()
        self._async_lock = asyncio.Lock()

    async def register_singleton(
        self,
        interface: Type[T],
        implementation: Type[T] | T
    ) -> None:
        """
        Register singleton service.

        Args:
            interface: Protocol/interface type
            implementation: Concrete implementation type or instance

        Example:
            >>> await container.register_singleton(MyProtocol, MyImplementation())
        """
        with self._lock:
            descriptor = ServiceDescriptor(
                interface=interface,
                implementation=implementation,
                lifecycle=Lifecycle.SINGLETON
            )
            self._services[interface] = descriptor

            # If implementation is already an instance, cache it immediately
            if not isinstance(implementation, type):
                self._singletons[interface] = implementation

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
            >>> await container.register_transient(MyProtocol, MyImplementation)
        """
        with self._lock:
            self._services[interface] = ServiceDescriptor(
                interface=interface,
                implementation=implementation,
                lifecycle=Lifecycle.TRANSIENT
            )

    async def register_scoped(
        self,
        interface: Type[T],
        implementation: Type[T],
        scope_id: str | None = None
    ) -> None:
        """
        Register scoped service.

        Args:
            interface: Protocol/interface type
            implementation: Concrete implementation type
            scope_id: Optional scope identifier (defaults to "default")

        Example:
            >>> await container.register_scoped(MyProtocol, MyImplementation, scope_id="request_123")
        """
        with self._lock:
            self._services[interface] = ServiceDescriptor(
                interface=interface,
                implementation=implementation,
                lifecycle=Lifecycle.SCOPED
            )

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
            >>> def create_my_service(container: ServiceContainer) -> MyProtocol:
            ...     return MyImplementation(dep=await container.get(Dependency))
            ...
            >>> await container.register_factory(MyProtocol, create_my_service)
        """
        with self._lock:
            self._services[interface] = ServiceDescriptor(
                interface=interface,
                implementation=type(None),  # Not used for factories
                lifecycle=Lifecycle.SINGLETON,  # Factories typically singletons
                factory=factory
            )

    async def get(self, interface: Type[T]) -> T:
        """
        Resolve dependency by protocol.

        Thread-safe async resolution with lifecycle management.

        Args:
            interface: Protocol/interface type

        Returns:
            Service instance

        Raises:
            ValueError: If service not registered
            Exception: If instantiation fails

        Example:
            >>> service = await container.get(MyProtocol)
        """
        async with self._async_lock:
            descriptor = self._services.get(interface)

            if not descriptor:
                raise ValueError(f"Service not registered: {interface.__name__}")

            # SINGLETON
            if descriptor.lifecycle == Lifecycle.SINGLETON:
                if interface not in self._singletons:
                    if descriptor.factory:
                        # Factory function
                        result = descriptor.factory(self)
                        if asyncio.iscoroutine(result):
                            result = await result
                        self._singletons[interface] = result
                    else:
                        # Direct instantiation
                        impl = descriptor.implementation
                        if isinstance(impl, type):
                            self._singletons[interface] = impl()
                        else:
                            self._singletons[interface] = impl
                return self._singletons[interface]

            # TRANSIENT
            if descriptor.lifecycle == Lifecycle.TRANSIENT:
                if descriptor.factory:
                    result = descriptor.factory(self)
                    if asyncio.iscoroutine(result):
                        result = await result
                    return result
                impl = descriptor.implementation
                if isinstance(impl, type):
                    return impl()
                return impl

            # SCOPED
            if descriptor.lifecycle == Lifecycle.SCOPED:
                scope_id = "default"  # TODO: Make scope_id configurable per request
                if scope_id not in self._scoped:
                    self._scoped[scope_id] = {}

                scope_store = self._scoped[scope_id]

                if interface not in scope_store:
                    if descriptor.factory:
                        result = descriptor.factory(self)
                        if asyncio.iscoroutine(result):
                            result = await result
                        scope_store[interface] = result
                    else:
                        impl = descriptor.implementation
                        if isinstance(impl, type):
                            scope_store[interface] = impl()
                        else:
                            scope_store[interface] = impl

                return scope_store[interface]

            raise ValueError(f"Unsupported lifecycle: {descriptor.lifecycle}")

    def get_sync(self, interface: Type[T]) -> T | None:
        """
        Synchronous get for non-async contexts.

        Only returns already-instantiated singletons. Does not trigger instantiation.

        Args:
            interface: Protocol/interface type

        Returns:
            Service instance or None if not instantiated

        Example:
            >>> service = container.get_sync(MyProtocol)
            >>> if service:
            ...     # Use cached singleton
        """
        return self._singletons.get(interface)

    async def is_registered(self, interface: Type) -> bool:
        """
        Check if service is registered.

        Args:
            interface: Protocol/interface type

        Returns:
            True if registered, False otherwise

        Example:
            >>> if await container.is_registered(MyProtocol):
            ...     service = await container.get(MyProtocol)
        """
        return interface in self._services

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
        # For single-registration pattern, return list with one item
        if await self.is_registered(interface):
            instance = await self.get(interface)
            return [instance]

        return []

    def get_stats(self) -> dict[str, Any]:
        """
        Get container statistics.

        Returns:
            Dict with stats: registered_services, singleton_count, etc.

        Example:
            >>> stats = container.get_stats()
            >>> print(f"Registered: {stats['registered_services']}")
        """
        return {
            "registered_services": len(self._services),
            "singleton_count": len(self._singletons),
            "scoped_scopes": len(self._scoped),
            "lifecycle_breakdown": {
                "singleton": sum(1 for s in self._services.values() if s.lifecycle == Lifecycle.SINGLETON),
                "transient": sum(1 for s in self._services.values() if s.lifecycle == Lifecycle.TRANSIENT),
                "scoped": sum(1 for s in self._services.values() if s.lifecycle == Lifecycle.SCOPED),
            }
        }

    async def clear_scope(self, scope_id: str) -> None:
        """
        Clear scoped services for a scope.

        Args:
            scope_id: Scope identifier to clear

        Example:
            >>> await container.clear_scope("request_123")
        """
        async with self._async_lock:
            self._scoped.pop(scope_id, None)

    async def dispose(self) -> None:
        """
        Dispose container and clear all services.

        Example:
            >>> await container.dispose()
        """
        async with self._async_lock:
            self._services.clear()
            self._singletons.clear()
            self._scoped.clear()
