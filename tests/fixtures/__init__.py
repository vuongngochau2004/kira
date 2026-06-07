"""
Test fixtures package.

This package contains reusable pytest fixtures for testing protocols,
ABC implementations, and other components.
"""

from tests.fixtures.abc_fixtures import (
    abc_implementation,
    protocol_vs_abc,
    create_abc_mock,
    assert_abc_compliance,
    benchmark_abc_vs_protocol,
    mock_classification_strategy,
    mock_query_handler,
    mock_dependency_container,
)

__all__ = [
    "abc_implementation",
    "protocol_vs_abc",
    "create_abc_mock",
    "assert_abc_compliance",
    "benchmark_abc_vs_protocol",
    "mock_classification_strategy",
    "mock_query_handler",
    "mock_dependency_container",
]
