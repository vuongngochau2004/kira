"""
Test ABC compliance for QueryHandlerABC.

Verifies that handler implementations correctly inherit from QueryHandlerABC
and implement all required abstract methods.
"""

import pytest
from abc import ABC

from src.abc.handlers import QueryHandlerABC
from src.protocols.classification import Intent, ClassificationResult
from src.protocols.handlers import HandlerResult, HandlerConfig


class MockQueryHandler(QueryHandlerABC):
    """Mock handler for testing ABC compliance."""

    def __init__(self, config: HandlerConfig | None = None):
        self.config = config or HandlerConfig()
        self.name = "MockHandler"

    async def handle(
        self,
        query: str,
        user_id: str,
        classification: ClassificationResult,
        context: dict | None = None
    ) -> HandlerResult:
        """Mock handle implementation."""
        return HandlerResult(
            content=f"Mock response for: {query}",
            metadata={"handler": self.name}
        )

    async def handle_stream(
        self,
        query: str,
        user_id: str,
        classification: ClassificationResult,
        context: dict | None = None
    ):
        """Mock handle_stream implementation."""
        yield {"type": "content", "data": {"text": f"Mock stream for: {query}"}}
        yield {"type": "done"}

    def can_handle(self, classification: ClassificationResult) -> bool:
        """Mock can_handle implementation."""
        return classification.intent == Intent.RAG

    def get_config(self) -> HandlerConfig:
        """Mock get_config implementation."""
        return self.config

    def get_name(self) -> str:
        """Mock get_name implementation."""
        return self.name


def test_abc_is_abstract():
    """Test that QueryHandlerABC is an abstract base class."""
    assert issubclass(QueryHandlerABC, ABC)

    # Should not be able to instantiate ABC directly
    with pytest.raises(TypeError):
        QueryHandlerABC()


def test_mock_handler_is_instance():
    """Test that mock handler is instance of QueryHandlerABC."""
    handler = MockQueryHandler()
    assert isinstance(handler, QueryHandlerABC)


def test_mock_handler_has_all_methods():
    """Test that mock handler implements all required methods."""
    handler = MockQueryHandler()

    # Check all abstract methods are implemented
    assert hasattr(handler, 'handle')
    assert hasattr(handler, 'handle_stream')
    assert hasattr(handler, 'can_handle')
    assert hasattr(handler, 'get_config')
    assert hasattr(handler, 'get_name')

    # Check methods are callable
    assert callable(handler.handle)
    assert callable(handler.handle_stream)
    assert callable(handler.can_handle)
    assert callable(handler.get_config)
    assert callable(handler.get_name)


def test_mock_handler_methods_work():
    """Test that mock handler methods work correctly."""
    import asyncio

    handler = MockQueryHandler()
    classification = ClassificationResult(
        intent=Intent.RAG,
        confidence=0.9,
        reason="Test classification"
    )

    # Test handle
    async def test_handle():
        result = await handler.handle("test query", "user123", classification)
        assert result.content == "Mock response for: test query"
        assert result.metadata["handler"] == "MockHandler"
        assert result.is_success()

    asyncio.run(test_handle())

    # Test handle_stream
    async def test_stream():
        chunks = []
        async for chunk in handler.handle_stream("test query", "user123", classification):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0]["type"] == "content"
        assert chunks[1]["type"] == "done"

    asyncio.run(test_stream())

    # Test can_handle
    assert handler.can_handle(classification) is True

    # Test get_config
    config = handler.get_config()
    assert isinstance(config, HandlerConfig)

    # Test get_name
    assert handler.get_name() == "MockHandler"


def test_handler_abc_matches_protocol():
    """Test that QueryHandlerABC has same methods as QueryHandler Protocol."""
    from src.protocols.handlers import QueryHandler

    abc_methods = {
        m for m in dir(QueryHandlerABC)
        if not m.startswith('_') and callable(getattr(QueryHandlerABC, m, None))
    }

    protocol_methods = {
        m for m in dir(QueryHandler)
        if not m.startswith('_') and callable(getattr(QueryHandler, m, None))
    }

    # ABC should have all Protocol methods
    assert protocol_methods.issubset(abc_methods), \
        f"ABC missing methods: {protocol_methods - abc_methods}"


def test_handler_has_correct_abstract_methods():
    """Test that QueryHandlerABC has correct abstract methods."""
    from abc import abstractmethod

    abstract_methods = []
    for name in dir(QueryHandlerABC):
        if not name.startswith('_'):
            attr = getattr(QueryHandlerABC, name)
            if getattr(attr, '__isabstractmethod__', False):
                abstract_methods.append(name)

    expected_abstracts = {
        'handle',
        'handle_stream',
        'can_handle',
        'get_config',
        'get_name'
    }

    assert set(abstract_methods) == expected_abstracts, \
        f"Abstract methods mismatch. Expected: {expected_abstracts}, Got: {set(abstract_methods)}"
