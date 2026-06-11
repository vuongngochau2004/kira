"""
Tests for ScopeManagerBase.
"""

import pytest

from src.shared.kernel.interfaces.container import ScopeManagerBase
from src.shared.kernel.interfaces.container import DependencyContainerBase


class MockScopeManager(ScopeManagerBase):
    """Mock ScopeManager implementation for testing."""

    def __init__(self):
        self._scopes = {}

    async def create_scope(self, scope_id: str) -> None:
        """Create a new scope."""
        self._scopes[scope_id] = {}

    async def get_scoped_service(
        self,
        interface,
        scope_id: str,
        container: DependencyContainerBase
    ):
        """Get service within scope."""
        if scope_id not in self._scopes:
            raise ValueError(f"Scope {scope_id} not created")

        if interface not in self._scopes[scope_id]:
            self._scopes[scope_id][interface] = await container.get(interface)

        return self._scopes[scope_id][interface]

    async def dispose_scope(self, scope_id: str) -> None:
        """Dispose scoped services."""
        if scope_id in self._scopes:
            del self._scopes[scope_id]


class MockService:
    """Mock service for testing."""

    def __init__(self, value: int = 0):
        self.value = value


class MockProtocol:
    """Mock protocol for testing."""

    pass


@pytest.mark.asyncio
async def test_interface_cannot_be_instantiated():
    """Test that ScopeManagerBase interface cannot be instantiated directly."""
    with pytest.raises(TypeError):
        ScopeManagerBase()


@pytest.mark.asyncio
async def test_concrete_implementation_works():
    """Test that concrete implementation of ScopeManagerBase works."""
    manager = MockScopeManager()

    await manager.create_scope("test_scope")
    assert "test_scope" in manager._scopes


@pytest.mark.asyncio
async def test_create_scope():
    """Test creating a scope."""
    manager = MockScopeManager()

    await manager.create_scope("request_123")

    assert "request_123" in manager._scopes
    assert manager._scopes["request_123"] == {}


@pytest.mark.asyncio
async def test_dispose_scope():
    """Test disposing a scope."""
    manager = MockScopeManager()

    await manager.create_scope("request_123")
    await manager.dispose_scope("request_123")

    assert "request_123" not in manager._scopes


@pytest.mark.asyncio
async def test_get_scoped_service():
    """Test getting scoped service."""
    from src.shared.kernel.di.container import ServiceContainer

    manager = MockScopeManager()
    container = ServiceContainer()

    # Register service
    await container.register_singleton(MockProtocol, MockService(value=42))

    # Create scope
    await manager.create_scope("test_scope")

    # Get scoped service
    service = await manager.get_scoped_service(MockProtocol, "test_scope", container)

    assert isinstance(service, MockService)
    assert service.value == 42


@pytest.mark.asyncio
async def test_scoped_service_cached_within_scope():
    """Test that scoped service is cached within same scope."""
    from src.shared.kernel.di.container import ServiceContainer

    manager = MockScopeManager()
    container = ServiceContainer()

    # Register service as singleton
    await container.register_singleton(MockProtocol, MockService)

    # Create scope
    await manager.create_scope("test_scope")

    # Get service twice
    service1 = await manager.get_scoped_service(MockProtocol, "test_scope", container)
    service2 = await manager.get_scoped_service(MockProtocol, "test_scope", container)

    # Should return same instance (cached in scope)
    assert service1 is service2


@pytest.mark.asyncio
async def test_get_scoped_service_from_nonexistent_scope():
    """Test getting service from non-existent scope raises error."""
    from src.shared.kernel.di.container import ServiceContainer

    manager = MockScopeManager()
    container = ServiceContainer()

    await container.register_singleton(MockProtocol, MockService)

    # Try to get service without creating scope
    with pytest.raises(ValueError, match="Scope .* not created"):
        await manager.get_scoped_service(MockProtocol, "nonexistent", container)


@pytest.mark.asyncio
async def test_dispose_nonexistent_scope():
    """Test disposing non-existent scope doesn't raise error."""
    manager = MockScopeManager()

    # Should not raise error
    await manager.dispose_scope("nonexistent")


@pytest.mark.asyncio
async def test_multiple_scopes():
    """Test managing multiple independent scopes."""
    from src.shared.kernel.di.container import ServiceContainer

    manager = MockScopeManager()
    container = ServiceContainer()

    await container.register_transient(MockProtocol, MockService)

    # Create multiple scopes
    await manager.create_scope("scope1")
    await manager.create_scope("scope2")

    # Get services in different scopes
    service1 = await manager.get_scoped_service(MockProtocol, "scope1", container)
    service2 = await manager.get_scoped_service(MockProtocol, "scope2", container)

    # Transient service - should be different instances
    assert service1 is not service2

    # But same within each scope
    service1_again = await manager.get_scoped_service(MockProtocol, "scope1", container)
    assert service1 is service1_again

    service2_again = await manager.get_scoped_service(MockProtocol, "scope2", container)
    assert service2 is service2_again


@pytest.mark.asyncio
async def test_interface_enforces_all_methods():
    """Test that interface enforces implementation of all abstract methods."""
    from abc import ABC

    # Try to create incomplete implementation
    class IncompleteScopeManager(ScopeManagerBase):
        async def create_scope(self, scope_id: str) -> None:
            pass

        # Missing get_scoped_service and dispose_scope

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteScopeManager()


@pytest.mark.asyncio
async def test_interface_has_abstractmethod_decorators():
    """Test that interface methods are properly marked as abstract."""
    from src.shared.kernel.interfaces.container import ScopeManagerBase

    # Check that methods are abstract
    assert hasattr(ScopeManagerBase.create_scope, '__isabstractmethod__')
    assert hasattr(ScopeManagerBase.get_scoped_service, '__isabstractmethod__')
    assert hasattr(ScopeManagerBase.dispose_scope, '__isabstractmethod__')
