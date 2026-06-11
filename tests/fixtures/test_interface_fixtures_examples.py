"""
Example tests demonstrating ABC fixtures usage.

This file shows how to use the ABC-compatible test fixtures for
Protocol to ABC migration testing.
"""

import pytest
from uuid import uuid4

from interfaces.classification import Intent, ClassificationResult
from interfaces.handlers import Citation, HandlerConfig

from tests.fixtures.abc_fixtures import (
    ClassificationStrategyBase,
    QueryHandlerBase,
    DependencyContainerBase,
    create_abc_mock,
    assert_abc_compliance,
)


# ============================================================================
# Basic ABC Implementation Tests
# ============================================================================

class TestABCImplementationBasics:
    """Test basic ABC implementation creation and usage."""

    def test_create_classification_abc_mock(self):
        """Test creating mock classification ABC implementation."""
        impl = create_abc_mock(ClassificationStrategyBase)
        assert impl is not None
        assert hasattr(impl, 'classify')
        assert hasattr(impl, 'can_handle')

    def test_create_query_handler_abc_mock(self):
        """Test creating mock query handler ABC implementation."""
        impl = create_abc_mock(QueryHandlerBase)
        assert impl is not None
        assert hasattr(impl, 'handle')
        assert hasattr(impl, 'can_handle')
        assert hasattr(impl, 'get_config')
        assert hasattr(impl, 'get_name')

    def test_create_container_abc_mock(self):
        """Test creating mock dependency container ABC implementation."""
        impl = create_abc_mock(DependencyContainerBase)
        assert impl is not None
        assert hasattr(impl, 'register_singleton')
        assert hasattr(impl, 'get')
        assert hasattr(impl, 'is_registered')


# ============================================================================
# ABC Compliance Tests
# ============================================================================

class TestABCCompliance:
    """Test ABC compliance validation."""

    def test_classification_abc_compliance(self):
        """Test that mock classification strategy complies with ABC."""
        from tests.fixtures.abc_fixtures import MockClassificationStrategyBase
        assert_abc_compliance(ClassificationStrategyBase, MockClassificationStrategyBase)

    def test_query_handler_abc_compliance(self):
        """Test that mock query handler complies with ABC."""
        from tests.fixtures.abc_fixtures import MockQueryHandlerBase
        assert_abc_compliance(QueryHandlerBase, MockQueryHandlerBase)

    def test_container_abc_compliance(self):
        """Test that mock container complies with ABC."""
        from tests.fixtures.abc_fixtures import MockDependencyContainerBase
        assert_abc_compliance(DependencyContainerBase, MockDependencyContainerBase)


# ============================================================================
# Fixture-Based Tests
# ============================================================================

class TestFixtureBasedABC:
    """Test ABC implementations using pytest fixtures."""

    def test_abc_implementation_fixture(self, abc_implementation):
        """Test abc_implementation fixture."""
        impl = abc_implementation(ClassificationStrategyBase)
        assert impl is not None
        assert hasattr(impl, 'classify')

    def test_protocol_vs_abc_fixture(self, protocol_vs_abc):
        """Test protocol_vs_abc comparison fixture."""
        from tests.fixtures.abc_fixtures import (
            MockClassificationStrategyProtocol,
            MockClassificationStrategyBase
        )

        protocol_impl, abc_impl = protocol_vs_abc(
            MockClassificationStrategyProtocol,
            ClassificationStrategyBase
        )

        assert protocol_impl is not None
        assert abc_impl is not None

    def test_mock_classification_strategy_fixture(self, mock_classification_strategy):
        """Test mock_classification_strategy fixture with custom config."""
        strategy = mock_classification_strategy(
            intent=Intent.CONVERSATIONAL,
            confidence=0.85
        )

        assert strategy is not None
        assert strategy.intent == Intent.CONVERSATIONAL
        assert strategy.confidence == 0.85

    def test_mock_query_handler_fixture(self, mock_query_handler):
        """Test mock_query_handler fixture with citations."""
        citations = [
            Citation(filename="test.pdf", page=1, text="Test content", confidence=0.9)
        ]

        handler = mock_query_handler(
            content="Custom response",
            citations=citations
        )

        assert handler is not None
        assert handler.content == "Custom response"
        assert len(handler.citations) == 1

    def test_mock_dependency_container_fixture(self, mock_dependency_container):
        """Test mock_dependency_container fixture."""
        container = mock_dependency_container()
        assert container is not None
        assert hasattr(container, 'register_singleton')
        assert hasattr(container, 'get')


# ============================================================================
# Async Tests with ABC Implementations
# ============================================================================

class TestABCAsyncExecution:
    """Test async execution of ABC implementations."""

    @pytest.mark.asyncio
    async def test_classification_async_execution(self, abc_implementation):
        """Test async classify method of ABC implementation."""
        impl = abc_implementation(ClassificationStrategyBase)
        result = await impl.classify("test query", uuid4())

        assert result is not None
        assert isinstance(result, ClassificationResult)
        assert result.intent == Intent.RAG
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_handler_async_execution(self, abc_implementation):
        """Test async handle method of ABC implementation."""
        classification = ClassificationResult(
            intent=Intent.RAG,
            confidence=0.9,
            reason="Test classification"
        )

        impl = abc_implementation(QueryHandlerBase)
        result = await impl.handle("test query", uuid4(), classification)

        assert result is not None
        assert result.is_success()
        assert result.content
        assert result.metadata

    @pytest.mark.asyncio
    async def test_container_async_registration(self, mock_dependency_container):
        """Test async service registration and resolution."""
        container = mock_dependency_container()

        # Register service
        await container.register_singleton(
            ClassificationStrategyBase,
            create_abc_mock(ClassificationStrategyBase)
        )

        # Resolve service
        strategy = await container.get(ClassificationStrategyBase)
        assert strategy is not None

        # Use service
        result = await strategy.classify("test", uuid4())
        assert result.intent == Intent.RAG

    @pytest.mark.asyncio
    async def test_container_singleton_behavior(self, mock_dependency_container):
        """Test that container returns same instance for singleton."""
        container = mock_dependency_container()

        # Register singleton
        await container.register_singleton(
            ClassificationStrategyBase,
            create_abc_mock(ClassificationStrategyBase)
        )

        # Resolve twice
        strategy1 = await container.get(ClassificationStrategyBase)
        strategy2 = await container.get(ClassificationStrategyBase)

        # Should be same instance
        assert strategy1 is strategy2

        # Call count should persist
        await strategy1.classify("test1", uuid4())
        await strategy2.classify("test2", uuid4())

        assert strategy1.call_count == 2
        assert strategy2.call_count == 2


# ============================================================================
# Protocol vs ABC Comparison Tests
# ============================================================================

class TestProtocolVsABCComparison:
    """Compare Protocol and ABC implementations."""

    @pytest.mark.asyncio
    async def test_classification_consistency(self, protocol_vs_abc):
        """Test that Protocol and ABC produce consistent results."""
        from tests.fixtures.abc_fixtures import (
            MockClassificationStrategyProtocol,
            MockClassificationStrategyBase
        )

        protocol_impl, abc_impl = protocol_vs_abc(
            MockClassificationStrategyProtocol,
            ClassificationStrategyBase
        )

        query = "test query"
        user_id = uuid4()

        result_protocol = await protocol_impl.classify(query, user_id)
        result_abc = await abc_impl.classify(query, user_id)

        # Both should return valid results
        assert result_protocol.intent == result_abc.intent
        assert result_protocol.confidence == result_abc.confidence

    @pytest.mark.asyncio
    async def test_handler_consistency(self, protocol_vs_abc):
        """Test handler consistency between Protocol and ABC."""
        from tests.fixtures.abc_fixtures import (
            MockQueryHandlerProtocol,
            MockQueryHandlerBase
        )

        protocol_impl, abc_impl = protocol_vs_abc(
            MockQueryHandlerProtocol,
            QueryHandlerBase
        )

        classification = ClassificationResult(
            intent=Intent.RAG,
            confidence=0.9,
            reason="Test"
        )

        result_protocol = await protocol_impl.handle("test", uuid4(), classification)
        result_abc = await abc_impl.handle("test", uuid4(), classification)

        # Both should return valid results
        assert result_protocol.is_success()
        assert result_abc.is_success()
        assert result_protocol.content == result_abc.content


# ============================================================================
# Performance Benchmark Tests
# ============================================================================

class TestABCBenchmarking:
    """Test performance benchmarking between Protocol and ABC."""

    @pytest.mark.asyncio
    async def test_benchmark_classification(self):
        """Benchmark classification Protocol vs ABC."""
        from tests.fixtures.abc_fixtures import (
            MockClassificationStrategyProtocol,
            benchmark_abc_vs_protocol
        )

        results = await benchmark_abc_vs_protocol(
            MockClassificationStrategyProtocol,
            ClassificationStrategyBase,
            iterations=100
        )

        assert "protocol_time" in results
        assert "abc_time" in results
        assert "speedup_ratio" in results
        assert "iterations" in results

        assert results["iterations"] == 100
        assert results["protocol_time"] > 0
        assert results["abc_time"] > 0
        assert results["speedup_ratio"] > 0

    @pytest.mark.asyncio
    async def test_benchmark_handler(self):
        """Benchmark handler Protocol vs ABC."""
        from tests.fixtures.abc_fixtures import (
            MockClassificationStrategyProtocol,
            benchmark_abc_vs_protocol
        )

        # Note: Can't benchmark MockQueryHandlerProtocol as it has no classify method
        # Use classification strategy for benchmarking instead
        results = await benchmark_abc_vs_protocol(
            MockClassificationStrategyProtocol,
            ClassificationStrategyBase,
            iterations=50
        )

        assert results["iterations"] == 50
        assert results["protocol_time"] > 0
        assert results["abc_time"] > 0


# ============================================================================
# Integration Tests with Complete Suite
# ============================================================================

class TestABCIntegrationSuite:
    """Integration tests using complete ABC migration suite."""

    @pytest.mark.asyncio
    async def test_full_classification_pipeline(self, abc_migration_suite):
        """Test complete classification pipeline with ABC."""
        suite = abc_migration_suite()

        # Use ABC strategy
        abc_strategy = suite["abc_strategy"]
        result = await abc_strategy.classify(
            suite["sample_query"],
            suite["sample_user_id"]
        )

        assert result is not None
        assert result.intent == Intent.RAG

    @pytest.mark.asyncio
    async def test_full_handler_pipeline(self, abc_migration_suite):
        """Test complete handler pipeline with ABC."""
        suite = abc_migration_suite()

        # Create classification
        classification = ClassificationResult(
            intent=Intent.RAG,
            confidence=0.9,
            reason="Test"
        )

        # Use ABC handler
        abc_handler = suite["abc_handler"]
        result = await abc_handler.handle(
            suite["sample_query"],
            suite["sample_user_id"],
            classification,
            suite["sample_context"]
        )

        assert result is not None
        assert result.is_success()

    @pytest.mark.asyncio
    async def test_container_with_services(self, abc_migration_suite):
        """Test container with registered services."""
        suite = abc_migration_suite()
        container = suite["abc_container"]

        # Register services
        await container.register_singleton(
            ClassificationStrategyBase,
            suite["abc_strategy"]
        )

        await container.register_singleton(
            QueryHandlerBase,
            suite["abc_handler"]
        )

        # Verify registration
        assert await container.is_registered(ClassificationStrategyBase)
        assert await container.is_registered(QueryHandlerBase)

        # Resolve and use
        strategy = await container.get(ClassificationStrategyBase)
        result = await strategy.classify("test", uuid4())
        assert result.intent == Intent.RAG

        # Check stats (singleton_count should be 1 since only strategy was resolved)
        stats = container.get_stats()
        assert stats["registration_count"] == 2
        assert stats["resolution_count"] == 1
        assert stats["singleton_count"] == 1  # Only strategy was instantiated


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestABCEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, abc_implementation):
        """Test handling of empty queries."""
        impl = abc_implementation(ClassificationStrategyBase)

        # Empty query should still work
        result = await impl.classify("", uuid4())
        assert result is not None

        # can_handle should return False for empty query
        assert not impl.can_handle("", uuid4())

    @pytest.mark.asyncio
    async def test_low_confidence_handling(self, abc_implementation):
        """Test handling of low confidence classifications."""
        handler = abc_implementation(QueryHandlerBase)

        # Low confidence classification
        classification = ClassificationResult(
            intent=Intent.RAG,
            confidence=0.3,  # Below 0.5 threshold
            reason="Low confidence"
        )

        # Handler should not handle low confidence
        assert not handler.can_handle(classification)

    @pytest.mark.asyncio
    async def test_unregistered_service_error(self, mock_dependency_container):
        """Test error handling for unregistered services."""
        container = mock_dependency_container()

        # Try to get unregistered service
        with pytest.raises(ValueError, match="not registered"):
            await container.get(QueryHandlerBase)

    @pytest.mark.asyncio
    async def test_abc_compliance_failure(self):
        """Test ABC compliance check with non-compliant implementation."""

        class NonCompliantImplementation:
            """Missing required abstract methods."""
            pass

        with pytest.raises(AssertionError, match="missing abstract method"):
            assert_abc_compliance(ClassificationStrategyBase, NonCompliantImplementation)


# ============================================================================
# Test Data Fixtures
# ============================================================================

class TestTestDataFixtures:
    """Test sample data fixtures."""

    def test_sample_classification_result(self, sample_classification_result):
        """Test sample classification result fixture."""
        assert sample_classification_result.intent == Intent.RAG
        assert sample_classification_result.confidence == 0.95
        assert "strategy" in sample_classification_result.metadata

    def test_sample_citations(self, sample_citations):
        """Test sample citations fixture."""
        assert len(sample_citations) == 2
        assert sample_citations[0].filename == "contract.pdf"
        assert sample_citations[1].filename == "policy.pdf"

    def test_sample_handler_config(self, sample_handler_config):
        """Test sample handler configuration fixture."""
        assert sample_handler_config.max_retrieved_docs == 10
        assert sample_handler_config.max_tokens == 4000
        assert sample_handler_config.temperature == 0.5
        assert sample_handler_config.streaming_enabled is True


# ============================================================================
# Protocol Compatibility Tests
# ============================================================================

class TestProtocolCompatibility:
    """Test Protocol compatibility verification."""

    def test_verify_protocol_compatibility(self):
        """Test protocol compatibility verification function."""
        from tests.fixtures.abc_fixtures import (
            MockClassificationStrategyProtocol,
            verify_protocol_compatibility,
            ClassificationStrategy
        )

        impl = MockClassificationStrategyProtocol()
        is_compatible = verify_protocol_compatibility(ClassificationStrategy, impl)

        assert is_compatible is True

    def test_measure_protocol_overhead(self):
        """Test measuring protocol execution overhead."""
        from tests.fixtures.abc_fixtures import (
            MockClassificationStrategyProtocol,
            measure_protocol_overhead
        )
        import asyncio

        impl = MockClassificationStrategyProtocol()

        # Measure async method
        overhead = measure_protocol_overhead(
            impl,
            "classify",
            "test query",
            "user123"
        )

        assert "method" in overhead
        assert overhead["method"] == "classify"
        assert "execution_time_ms" in overhead
        assert overhead["execution_time_ms"] > 0
        assert overhead["is_async"] is True
