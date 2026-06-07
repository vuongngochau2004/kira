"""
Tests for ServiceContainer.
"""

import pytest

from src.di.container import ServiceContainer
from src.interfaces.container import Lifecycle


class MockService:
    """Mock service for testing."""

    def __init__(self, value: int = 0):
        self.value = value


class MockProtocol:
    """Mock protocol for testing."""

    pass


@pytest.mark.asyncio
async def test_container_creation():
    """Test ServiceContainer creation."""
    container = ServiceContainer()

    stats = container.get_stats()

    assert stats["registered_services"] == 0
    assert stats["singleton_count"] == 0


@pytest.mark.asyncio
async def test_register_singleton():
    """Test registering singleton service."""
    container = ServiceContainer()

    await container.register_singleton(MockProtocol, MockService())

    stats = container.get_stats()
    assert stats["registered_services"] == 1
    assert await container.is_registered(MockProtocol)


@pytest.mark.asyncio
async def test_register_singleton_with_instance():
    """Test registering singleton with pre-created instance."""
    container = ServiceContainer()
    instance = MockService(value=42)

    await container.register_singleton(MockProtocol, instance)

    # Should return same instance
    service = await container.get(MockProtocol)
    assert service.value == 42

    # Should be cached (same instance)
    service2 = await container.get(MockProtocol)
    assert service is service2


@pytest.mark.asyncio
async def test_singleton_returns_same_instance():
    """Test singleton returns same instance on multiple calls."""
    container = ServiceContainer()

    await container.register_singleton(MockProtocol, MockService)

    service1 = await container.get(MockProtocol)
    service2 = await container.get(MockProtocol)

    assert service1 is service2


@pytest.mark.asyncio
async def test_register_transient():
    """Test registering transient service."""
    container = ServiceContainer()

    await container.register_transient(MockProtocol, MockService)

    stats = container.get_stats()
    assert stats["registered_services"] == 1
    assert await container.is_registered(MockProtocol)


@pytest.mark.asyncio
async def test_transient_returns_new_instance():
    """Test transient returns new instance on each call."""
    container = ServiceContainer()

    await container.register_transient(MockProtocol, MockService)

    service1 = await container.get(MockProtocol)
    service2 = await container.get(MockProtocol)

    assert service1 is not service2
    assert isinstance(service1, MockService)
    assert isinstance(service2, MockService)


@pytest.mark.asyncio
async def test_register_scoped():
    """Test registering scoped service."""
    container = ServiceContainer()

    await container.register_scoped(MockProtocol, MockService, scope_id="test_scope")

    stats = container.get_stats()
    assert stats["registered_services"] == 1
    assert await container.is_registered(MockProtocol)


@pytest.mark.asyncio
async def test_scoped_returns_same_instance_within_scope():
    """Test scoped returns same instance within scope."""
    container = ServiceContainer()

    await container.register_scoped(MockProtocol, MockService)

    service1 = await container.get(MockProtocol)
    service2 = await container.get(MockProtocol)

    # Same instance within same scope
    assert service1 is service2


@pytest.mark.asyncio
async def test_clear_scope():
    """Test clearing scoped services."""
    container = ServiceContainer()

    await container.register_scoped(MockProtocol, MockService)
    await container.get(MockProtocol)  # Create instance

    await container.clear_scope("default")

    # Should create new instance after clear
    service = await container.get(MockProtocol)
    assert isinstance(service, MockService)


@pytest.mark.asyncio
async def test_register_factory():
    """Test registering factory function."""
    container = ServiceContainer()

    def create_service(c):
        return MockService(value=99)

    await container.register_factory(MockProtocol, create_service)

    service = await container.get(MockProtocol)

    assert service.value == 99


@pytest.mark.asyncio
async def test_factory_with_async_function():
    """Test factory with async function."""
    container = ServiceContainer()

    async def create_service_async(c):
        return MockService(value=88)

    await container.register_factory(MockProtocol, create_service_async)

    service = await container.get(MockProtocol)

    assert service.value == 88


@pytest.mark.asyncio
async def test_get_sync_returns_cached():
    """Test get_sync returns only cached instances."""
    container = ServiceContainer()

    await container.register_singleton(MockProtocol, MockService)

    # Not yet instantiated
    service = container.get_sync(MockProtocol)
    assert service is None

    # Instantiate first
    await container.get(MockProtocol)

    # Now available in sync
    service = container.get_sync(MockProtocol)
    assert isinstance(service, MockService)


@pytest.mark.asyncio
async def test_get_all_with_single_registration():
    """Test get_all returns list with single registration."""
    container = ServiceContainer()

    await container.register_singleton(MockProtocol, MockService)

    services = await container.get_all(MockProtocol)

    assert len(services) == 1
    assert isinstance(services[0], MockService)


@pytest.mark.asyncio
async def test_get_all_with_no_registration():
    """Test get_all returns empty list when not registered."""
    container = ServiceContainer()

    services = await container.get_all(MockProtocol)

    assert len(services) == 0


@pytest.mark.asyncio
async def test_get_stats_breakdown():
    """Test get_stats includes lifecycle breakdown."""
    container = ServiceContainer()

    await container.register_singleton(MockProtocol, MockService)
    await container.register_transient(str, MockService)

    stats = container.get_stats()

    assert stats["lifecycle_breakdown"]["singleton"] == 1
    assert stats["lifecycle_breakdown"]["transient"] == 1


@pytest.mark.asyncio
async def test_get_nonexistent_service():
    """Test getting non-existent service raises error."""
    container = ServiceContainer()

    with pytest.raises(ValueError, match="Service not registered"):
        await container.get(MockProtocol)


@pytest.mark.asyncio
async def test_dispose():
    """Test disposing container."""
    container = ServiceContainer()

    await container.register_singleton(MockProtocol, MockService)
    await container.get(MockProtocol)  # Instantiate

    await container.dispose()

    stats = container.get_stats()
    assert stats["registered_services"] == 0
    assert stats["singleton_count"] == 0


@pytest.mark.asyncio
async def test_lifecycle_breakdown():
    """Test lifecycle breakdown in stats."""
    container = ServiceContainer()

    await container.register_singleton(MockProtocol, MockService)
    await container.register_transient(str, MockService)
    await container.register_scoped(int, MockService)

    stats = container.get_stats()

    assert stats["lifecycle_breakdown"]["singleton"] == 1
    assert stats["lifecycle_breakdown"]["transient"] == 1
    assert stats["lifecycle_breakdown"]["scoped"] == 1
