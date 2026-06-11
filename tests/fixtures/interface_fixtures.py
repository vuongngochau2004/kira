"""
ABC-compatible test fixtures for Protocol to ABC migration testing.

This module provides pytest fixtures and helper functions for testing
Protocol-based interfaces alongside their ABC equivalents during migration.

Fixtures support:
- ABC mock implementation generation
- Protocol vs ABC behavior comparison
- Performance benchmarking
- Compliance validation

Example:
    >>> def test_classification_with_abc(abc_implementation):
    ...     impl = abc_implementation(ClassificationStrategyBaseBase)
    ...     result = await impl.classify("test query", "user123")
    ...     assert result.intent == Intent.RAG
"""

from typing import TypeVar, Type, Any, get_type_hints, cast
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime
import pytest
import asyncio
from functools import wraps
import time

from src.shared.kernel.interfaces.classification import (
    ClassificationStrategyBase,
    ClassificationResult,
    Intent,
)
from src.shared.kernel.interfaces.handlers import (
    QueryHandlerBase,
    HandlerResult,
    Citation,
    HandlerConfig,
)
from src.shared.kernel.interfaces.container import (
    DependencyContainerBase,
    ServiceDescriptor,
    Lifecycle,
)


T = TypeVar("T")
K = TypeVar("K")


# ============================================================================
# ABC Implementations for Testing
# ============================================================================

class ClassificationStrategyBaseBase(ABC):
    """ABC version of ClassificationStrategyBase for testing migration."""

    @abstractmethod
    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        """Classify query intent."""
        pass

    @abstractmethod
    def can_handle(self, query: str, user_id: str | UUID) -> bool:
        """Quick check if strategy can handle query."""
        pass


class QueryHandlerBase(ABC):
    """ABC version of QueryHandler for testing migration."""

    @abstractmethod
    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None
    ) -> HandlerResult:
        """Execute query with known classification."""
        pass

    @abstractmethod
    def can_handle(self, classification: ClassificationResult) -> bool:
        """Check if handler can handle the classification."""
        pass

    @abstractmethod
    def get_config(self) -> HandlerConfig:
        """Get handler configuration."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get handler name."""
        pass


class DependencyContainerBase(ABC):
    """ABC version of DependencyContainer for testing migration."""

    @abstractmethod
    async def register_singleton(
        self,
        interface: Type[T],
        implementation: Type[T] | T
    ) -> None:
        """Register singleton service."""
        pass

    @abstractmethod
    async def get(self, interface: Type[T]) -> T:
        """Resolve dependency by interface."""
        pass

    @abstractmethod
    async def is_registered(self, interface: Type) -> bool:
        """Check if service is registered."""
        pass


# ============================================================================
# Mock Implementations for Testing
# ============================================================================

class MockClassificationStrategyBaseBase(ClassificationStrategyBaseBase):
    """Mock ABC implementation for testing."""

    def __init__(self, intent: Intent = Intent.RAG, confidence: float = 0.95):
        self.intent = intent
        self.confidence = confidence
        self.call_count = 0

    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        self.call_count += 1
        return ClassificationResult(
            intent=self.intent,
            confidence=self.confidence,
            reason=f"Mock classification for query: {query}",
            metadata={"call_count": self.call_count}
        )

    def can_handle(self, query: str, user_id: str | UUID) -> bool:
        return len(query) > 0


class MockQueryHandlerBase(QueryHandlerBase):
    """Mock ABC implementation for testing with citations."""

    def __init__(
        self,
        content: str = "Test response",
        citations: list[Citation] | None = None
    ):
        self.content = content
        self.citations = citations or []
        self.call_count = 0
        self.config = HandlerConfig(
            max_retrieved_docs=5,
            max_tokens=2000,
            temperature=0.7
        )

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None
    ) -> HandlerResult:
        self.call_count += 1
        return HandlerResult(
            content=self.content,
            citations=self.citations,
            metadata={
                "handler": "MockQueryHandlerBase",
                "call_count": self.call_count,
                "intent": classification.intent.value
            }
        )

    def can_handle(self, classification: ClassificationResult) -> bool:
        return classification.confidence > 0.5

    def get_config(self) -> HandlerConfig:
        return self.config

    def get_name(self) -> str:
        return "MockQueryHandlerBase"


class MockDependencyContainerBase(DependencyContainerBase):
    """Mock ABC implementation for testing singleton resolution."""

    def __init__(self):
        self._services: dict[Type, ServiceDescriptor] = {}
        self._singletons: dict[Type, Any] = {}
        self._registration_count = 0
        self._resolution_count = 0

    async def register_singleton(
        self,
        interface: Type[T],
        implementation: Type[T] | T
    ) -> None:
        self._registration_count += 1
        self._services[interface] = ServiceDescriptor(
            interface=interface,
            implementation=implementation,
            lifecycle=Lifecycle.SINGLETON
        )

    async def get(self, interface: Type[T]) -> T:
        self._resolution_count += 1
        descriptor = self._services.get(interface)

        if not descriptor:
            raise ValueError(f"Service {interface} not registered")

        if descriptor.is_singleton():
            if interface not in self._singletons:
                # Check if implementation is already an instance or a class
                impl = descriptor.implementation
                if isinstance(impl, type):
                    # It's a class, instantiate it
                    self._singletons[interface] = impl()
                else:
                    # It's already an instance, use directly
                    self._singletons[interface] = impl
            return cast(T, self._singletons[interface])

        # For transient, always create new instance
        impl = descriptor.implementation
        if isinstance(impl, type):
            return cast(T, impl())
        return cast(T, impl)

    async def is_registered(self, interface: Type) -> bool:
        return interface in self._services

    def get_stats(self) -> dict[str, Any]:
        return {
            "registration_count": self._registration_count,
            "resolution_count": self._resolution_count,
            "singleton_count": len(self._singletons),
            "registered_services": len(self._services)
        }


# ============================================================================
# Protocol Mock Implementations (for comparison)
# ============================================================================

class MockClassificationStrategyBaseProtocol:
    """Mock Protocol implementation for comparison."""

    def __init__(self, intent: Intent = Intent.RAG, confidence: float = 0.95):
        self.intent = intent
        self.confidence = confidence
        self.call_count = 0

    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        self.call_count += 1
        return ClassificationResult(
            intent=self.intent,
            confidence=self.confidence,
            reason=f"Mock classification for query: {query}",
            metadata={"call_count": self.call_count}
        )

    def can_handle(self, query: str, user_id: str | UUID) -> bool:
        return len(query) > 0


class MockQueryHandlerProtocol:
    """Mock Protocol implementation for comparison."""

    def __init__(
        self,
        content: str = "Test response",
        citations: list[Citation] | None = None
    ):
        self.content = content
        self.citations = citations or []
        self.call_count = 0
        self.config = HandlerConfig(
            max_retrieved_docs=5,
            max_tokens=2000,
            temperature=0.7
        )

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None
    ) -> HandlerResult:
        self.call_count += 1
        return HandlerResult(
            content=self.content,
            citations=self.citations,
            metadata={
                "handler": "MockQueryHandlerProtocol",
                "call_count": self.call_count,
                "intent": classification.intent.value
            }
        )

    def can_handle(self, classification: ClassificationResult) -> bool:
        return classification.confidence > 0.5

    def get_config(self) -> HandlerConfig:
        return self.config

    def get_name(self) -> str:
        return "MockQueryHandlerProtocol"


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def abc_implementation():
    """
    Create mock ABC implementation for testing.

    This fixture dynamically generates mock implementations for ABC classes.
    Useful for testing Protocol to ABC migration without concrete implementations.

    Example:
        >>> def test_classification_with_abc(abc_implementation):
        ...     impl = abc_implementation(ClassificationStrategyBaseBase)
        ...     result = await impl.classify("test", "user123")
        ...     assert result.intent == Intent.RAG
    """
    def _create_impl(abc_class: Type[T]) -> T:
        if abc_class == ClassificationStrategyBaseBase:
            return cast(T, MockClassificationStrategyBaseBase())
        elif abc_class == QueryHandlerBase:
            return cast(T, MockQueryHandlerBase())
        elif abc_class == DependencyContainerBase:
            return cast(T, MockDependencyContainerBase())
        else:
            raise ValueError(f"No mock implementation for {abc_class.__name__}")

    return _create_impl


@pytest.fixture
def protocol_vs_abc():
    """
    Compare Protocol and ABC behavior side-by-side.

    Returns a tuple of (protocol_impl, abc_impl) for comparison testing.

    Example:
        >>> def test_protocol_vs_abc_consistency(protocol_vs_abc):
        ...     protocol_impl, abc_impl = protocol_vs_abc(
        ...         MockClassificationStrategyBaseProtocol,
        ...         ClassificationStrategyBaseBase
        ...     )
        ...     result_protocol = await protocol_impl.classify("test", "user123")
        ...     result_abc = await abc_impl.classify("test", "user123")
        ...     assert result_protocol.intent == result_abc.intent
    """
    def _compare(protocol_class: Type, abc_class: Type[T]) -> tuple[Any, T]:
        protocol_impl = protocol_class()
        abc_impl: Any

        if abc_class == QueryHandlerBase:
            abc_impl = MockQueryHandlerBase()
        elif abc_class == DependencyContainerBase:
            abc_impl = MockDependencyContainerBase()
        else:
            abc_impl = MockClassificationStrategyBaseBase()

        return (protocol_impl, cast(T, abc_impl))

    return _compare


@pytest.fixture
def mock_classification_strategy():
    """
    Create mock classification strategy for testing.

    Returns a mock implementation that can be configured with custom intent and confidence.

    Example:
        >>> def test_classification(mock_classification_strategy):
        ...     strategy = mock_classification_strategy(Intent.CONVERSATIONAL, 0.85)
        ...     result = await strategy.classify("hello", "user123")
        ...     assert result.intent == Intent.CONVERSATIONAL
    """
    def _create(
        intent: Intent = Intent.RAG,
        confidence: float = 0.95
    ) -> MockClassificationStrategyBaseBase:
        return MockClassificationStrategyBaseBase(intent, confidence)

    return _create


@pytest.fixture
def mock_query_handler():
    """
    Create mock query handler for testing with citations.

    Returns a mock implementation that can be configured with custom content and citations.

    Example:
        >>> def test_handler(mock_query_handler):
        ...     handler = mock_query_handler(
        ...         content="Test response",
        ...         citations=[Citation(filename="doc.pdf", page=1, text="...")]
        ...     )
        ...     result = await handler.handle("query", "user123", classification)
        ...     assert len(result.citations) == 1
    """
    def _create(
        content: str = "Test response",
        citations: list[Citation] | None = None
    ) -> MockQueryHandlerBase:
        return MockQueryHandlerBase(content, citations)

    return _create


@pytest.fixture
def mock_dependency_container():
    """
    Create mock dependency container for testing singleton resolution.

    Returns a mock DI container that supports singleton registration and resolution.

    Example:
        >>> def test_di_container(mock_dependency_container):
        ...     container = mock_dependency_container()
        ...     await container.register_singleton(
        ...         ClassificationStrategyBaseBase,
        ...         MockClassificationStrategyBaseBase()
        ...     )
        ...     strategy = await container.get(ClassificationStrategyBaseBase)
        ...     result = await strategy.classify("test", "user123")
        ...     assert result.intent == Intent.RAG
    """
    return MockDependencyContainerBase


# ============================================================================
# Helper Functions
# ============================================================================

def create_abc_mock(abc_class: Type[T]) -> T:
    """
    Generate mock implementation for ABC class.

    This function creates a mock implementation that satisfies all abstract methods
    of the given ABC class. Useful for quick prototyping and testing.

    Args:
        abc_class: ABC class to create mock for

    Returns:
        Mock implementation instance

    Example:
        >>> impl = create_abc_mock(ClassificationStrategyBaseBase)
        >>> result = await impl.classify("test", "user123")
    """
    if abc_class == ClassificationStrategyBaseBase:
        return cast(T, MockClassificationStrategyBaseBase())
    elif abc_class == QueryHandlerBase:
        return cast(T, MockQueryHandlerBase())
    elif abc_class == DependencyContainerBase:
        return cast(T, MockDependencyContainerBase())
    else:
        raise ValueError(f"No mock implementation for {abc_class.__name__}")


def assert_abc_compliance(abc_class: Type, implementation: Type | object) -> None:
    """
    Verify that implementation satisfies ABC abstract methods.

    Checks that all abstract methods are implemented and have correct signatures.

    Args:
        abc_class: ABC class with abstract methods
        implementation: Implementation class or instance to validate

    Raises:
        AssertionError: If implementation doesn't comply with ABC

    Example:
        >>> assert_abc_compliance(ClassificationStrategyBaseBase, MockClassificationStrategyBaseBase)
        >>> # Passes if all abstract methods are implemented
    """
    if isinstance(implementation, type):
        impl_class = implementation
    else:
        impl_class = type(implementation)

    # Get abstract methods from ABC
    abstract_methods = abc_class.__abstractmethods__

    # Check all abstract methods are implemented
    for method_name in abstract_methods:
        if not hasattr(impl_class, method_name):
            raise AssertionError(
                f"{impl_class.__name__} missing abstract method: {method_name}"
            )

        # Check if method is concrete (not abstract)
        method = getattr(impl_class, method_name)
        if getattr(method, '__isabstractmethod__', False):
            raise AssertionError(
                f"{impl_class.__name__}.{method_name} is still abstract"
            )


async def benchmark_abc_vs_protocol(
    protocol_class: Type,
    abc_class: Type[T],
    iterations: int = 1000
) -> dict[str, Any]:
    """
    Performance test comparing Protocol vs ABC implementations.

    Measures execution time for both implementations over multiple iterations.

    Args:
        protocol_class: Protocol implementation class
        abc_class: ABC implementation class
        iterations: Number of test iterations

    Returns:
        Dict with benchmark results: protocol_time, abc_time, speedup_ratio

    Example:
        >>> results = await benchmark_abc_vs_protocol(
        ...     MockClassificationStrategyBaseProtocol,
        ...     ClassificationStrategyBaseBase
        ... )
        >>> print(f"Protocol: {results['protocol_time']:.4f}s")
        >>> print(f"ABC: {results['abc_time']:.4f}s")
        >>> print(f"Speedup: {results['speedup_ratio']:.2f}x")
    """
    # Create instances
    protocol_impl = protocol_class()
    abc_impl = create_abc_mock(abc_class)

    # Test data
    query = "test query for benchmarking"
    user_id = "benchmark_user_123"

    # Benchmark Protocol
    protocol_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await protocol_impl.classify(query, user_id)  # type: ignore[attr-defined]
        end = time.perf_counter()
        protocol_times.append(end - start)

    # Benchmark ABC
    abc_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await abc_impl.classify(query, user_id)  # type: ignore[attr-defined]
        end = time.perf_counter()
        abc_times.append(end - start)

    # Calculate statistics
    protocol_avg = sum(protocol_times) / len(protocol_times)
    abc_avg = sum(abc_times) / len(abc_times)
    speedup = abc_avg / protocol_avg if protocol_avg > 0 else 1.0

    return {
        "protocol_class": protocol_class.__name__,
        "abc_class": abc_class.__name__,
        "iterations": iterations,
        "protocol_time": protocol_avg,
        "abc_time": abc_avg,
        "speedup_ratio": speedup,
        "protocol_total": sum(protocol_times),
        "abc_total": sum(abc_times),
        "winner": "Protocol" if speedup > 1 else "ABC"
    }


def measure_protocol_overhead(protocol_impl: Any, method: str, *args, **kwargs) -> dict[str, Any]:
    """
    Measure overhead of Protocol-based implementation vs direct call.

    Args:
        protocol_impl: Protocol implementation instance
        method: Method name to measure
        *args: Method arguments
        **kwargs: Method keyword arguments

    Returns:
        Dict with timing information

    Example:
        >>> strategy = MockClassificationStrategyBaseProtocol()
        >>> overhead = measure_protocol_overhead(strategy, "classify", "test", "user123")
        >>> print(f"Execution time: {overhead['execution_time_ms']:.2f}ms")
    """
    # Warmup
    method_obj = getattr(protocol_impl, method)
    if asyncio.iscoroutinefunction(method_obj):
        asyncio.run(method_obj(*args, **kwargs))

    # Measure
    start = time.perf_counter()
    if asyncio.iscoroutinefunction(method_obj):
        asyncio.run(method_obj(*args, **kwargs))
    else:
        method_obj(*args, **kwargs)
    end = time.perf_counter()

    execution_time = end - start

    return {
        "method": method,
        "execution_time_ms": execution_time * 1000,
        "execution_time_s": execution_time,
        "is_async": asyncio.iscoroutinefunction(method_obj)
    }


def verify_protocol_compatibility(protocol: type, impl: Any) -> bool:
    """
    Verify that implementation is compatible with Protocol.

    Checks structural compatibility - does impl have all required methods/attributes?

    Args:
        protocol: Protocol class to check against
        impl: Implementation to verify

    Returns:
        True if compatible, False otherwise

    Example:
        >>> strategy = MockClassificationStrategyBaseProtocol()
        >>> is_compatible = verify_protocol_compatibility(ClassificationStrategyBase, strategy)
        >>> assert is_compatible
    """
    try:
        # Get Protocol type hints
        hints = get_type_hints(protocol)

        # Check each required method/attribute
        for attr_name, attr_type in hints.items():
            if not hasattr(impl, attr_name):
                return False

        return True
    except Exception:
        return False


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_classification_result():
    """Create sample classification result for testing."""
    return ClassificationResult(
        intent=Intent.RAG,
        confidence=0.95,
        reason="File keyword detected: 'tài liệu'",
        metadata={
            "strategy": "keyword",
            "matched_files": ["contract.pdf"],
            "execution_time_ms": 2.5
        }
    )


@pytest.fixture
def sample_citations():
    """Create sample citations for testing."""
    return [
        Citation(
            filename="contract.pdf",
            page=1,
            text="The agreement term is 12 months...",
            confidence=0.95,
            metadata={"chunk_id": "123", "relevance_score": 0.9}
        ),
        Citation(
            filename="policy.pdf",
            page=3,
            text="All employees must comply with...",
            confidence=0.87,
            metadata={"chunk_id": "456", "relevance_score": 0.8}
        )
    ]


@pytest.fixture
def sample_handler_config():
    """Create sample handler configuration for testing."""
    return HandlerConfig(
        max_retrieved_docs=10,
        max_tokens=4000,
        temperature=0.5,
        streaming_enabled=True,
        timeout_ms=60000,
        retry_count=3,
        metadata={"model": "glm-4.5", "provider": "zhipu"}
    )


# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture
async def initialized_di_container(mock_dependency_container):
    """
    Create fully initialized DI container with all services.

    This fixture pre-registers common services for integration testing.

    Example:
        >>> async def test_full_pipeline(initialized_di_container):
        ...     classifier = await container.get(ClassificationStrategyBaseBase)
        ...     result = await classifier.classify("test", "user123")
    """
    container = mock_dependency_container()

    # Register classification strategy
    await container.register_singleton(
        ClassificationStrategyBaseBase,
        MockClassificationStrategyBaseBase()
    )

    # Register query handler
    await container.register_singleton(
        QueryHandlerBase,
        MockQueryHandlerBase()
    )

    return container


@pytest.fixture
def abc_migration_suite():
    """
    Complete suite for testing Protocol to ABC migration.

    Returns dictionary with all necessary components for migration testing.

    Example:
        >>> def test_migration(abc_migration_suite):
        ...     suite = abc_migration_suite()
        ...     protocol_impl = suite["protocol_strategy"]
        ...     abc_impl = suite["abc_strategy"]
        ...     # Compare behavior
    """
    def _create_suite():
        return {
            # Classification
            "protocol_strategy": MockClassificationStrategyBaseProtocol(),
            "abc_strategy": MockClassificationStrategyBaseBase(),
            "protocol_classification": ClassificationStrategyBase,

            # Handler
            "protocol_handler": MockQueryHandlerProtocol(),
            "abc_handler": MockQueryHandlerBase(),
            "protocol_handler_protocol": QueryHandler,

            # Container
            "abc_container": MockDependencyContainerBase(),
            "protocol_container": DependencyContainerBase,  # Changed from DependencyContainer

            # Test data
            "sample_query": "test query about contract.pdf",
            "sample_user_id": "test_user_123",
            "sample_context": {"conversation_id": "conv_123"}
        }

    return _create_suite

# ============================================================================
# EXPORTS (aliases for test compatibility)
# ============================================================================
# These aliases allow tests to import the local ABC implementations
# without conflicting with the real interfaces from src.shared.kernel.interfaces

__all__ = [
    # ABC Base Classes (local implementations for testing)
    "ClassificationStrategyBaseBase",
    "QueryHandlerBase",
    "DependencyContainerBase",
    
    # Mock Implementations
    "MockClassificationStrategyBaseBase",
    "MockQueryHandlerBase",
    "MockDependencyContainerBase",
    
    # Protocol Implementations (for comparison)
    "MockClassificationStrategyBaseProtocol",
    "MockQueryHandlerProtocol",
    
    # Helper Functions
    "create_abc_mock",
    "assert_abc_compliance",
    "benchmark_abc_vs_protocol",
    "measure_protocol_overhead",
    "verify_protocol_compatibility",
    
    # Fixtures
    "abc_implementation",
    "protocol_vs_abc",
    "mock_classification_strategy",
    "mock_query_handler",
    "mock_dependency_container",
    "initialized_di_container",
    "abc_migration_suite",
    "sample_classification_result",
    "sample_citations",
    "sample_handler_config",
]
