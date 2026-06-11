"""Integration tests for tool registry with 4-agent architecture."""

import pytest
from unittest.mock import Mock

from tools.tool_registry import (
    ToolRegistry,
    initialize_tool_registry,
    get_tools_for_langgraph,
)


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for tool registry."""
    return {
        "qdrant_store": Mock(),
        "bm25_index": Mock(),
        "embedding_fn": Mock(return_value=[0.1, 0.2, 0.3]),
        "llm_client": Mock()
    }


def test_tool_registry_initialization(mock_dependencies):
    """Test tool registry initialization with dependencies."""
    registry = ToolRegistry()

    assert registry._initialized is False

    registry.initialize_dependencies(
        qdrant_store=mock_dependencies["qdrant_store"],
        bm25_index=mock_dependencies["bm25_index"],
        embedding_fn=mock_dependencies["embedding_fn"],
        llm_client=mock_dependencies["llm_client"],
    )

    assert registry._initialized is True


def test_tool_registry_register_all_tools(mock_dependencies):
    """Test registering all tools."""
    registry = initialize_tool_registry(**mock_dependencies)

    tool_names = registry.get_tool_names()
    assert len(tool_names) > 0

    # Check for expected tools
    expected_tools = [
        "dense_retrieve",
        "hybrid_retrieve",
        "query_expansion_tool",
        "generate_tool",
        "critique_response_tool",
        "verify_facts_tool",
    ]

    for tool_name in expected_tools:
        assert tool_name in tool_names


def test_get_tools_by_agent_type(mock_dependencies):
    """Test getting tools by agent type."""
    registry = initialize_tool_registry(**mock_dependencies)

    # RetrievalAgent tools
    retrieval_tools = registry.get_retrieval_tools()
    assert len(retrieval_tools) > 0
    tool_names = [t.name for t in retrieval_tools if hasattr(t, 'name')]
    assert "hybrid_retrieve_with_expansion" in tool_names

    # GenerationAgent tools
    generation_tools = registry.get_generation_tools()
    assert len(generation_tools) > 0

    # QualityAgent tools
    quality_tools = registry.get_quality_tools()
    assert len(quality_tools) > 0
    quality_names = [t.name for t in quality_tools if hasattr(t, 'name')]
    assert "combined_quality_assessment" in quality_names

    # OrchestratorAgent should get all tools
    orchestrator_tools = registry.get_tools_for_agent("OrchestratorAgent")
    assert len(orchestrator_tools) >= len(retrieval_tools)


def test_get_specific_tool(mock_dependencies):
    """Test getting a specific tool by name."""
    registry = initialize_tool_registry(**mock_dependencies)

    tool = registry.get_tool("hybrid_retrieve")
    assert tool is not None


def test_get_tools_for_langgraph_function(mock_dependencies):
    """Test get_tools_for_langgraph convenience function."""
    tools = get_tools_for_langgraph("RetrievalAgent")
    assert len(tools) > 0


def test_global_registry_instance():
    """Test global registry instance."""
    from tools.tool_registry import get_tool_registry, _global_registry

    # First call should create instance
    registry1 = get_tool_registry()
    assert registry1 is not None

    # Second call should return same instance
    registry2 = get_tool_registry()
    assert registry1 is registry2


def test_list_tools_by_category(mock_dependencies):
    """Test listing tools by category."""
    registry = initialize_tool_registry(**mock_dependencies)

    categorized = registry.list_tools_by_category()

    assert "retrieval" in categorized
    assert "generation" in categorized
    assert "quality" in categorized
    assert "reranking" in categorized


def test_tool_registry_error_handling():
    """Test error handling in tool registry."""
    registry = ToolRegistry()

    # Should raise error if trying to register tools without initialization
    with pytest.raises(RuntimeError, match="Must initialize dependencies"):
        registry.register_all_tools()


def test_unknown_agent_type(mock_dependencies):
    """Test handling of unknown agent type."""
    registry = initialize_tool_registry(**mock_dependencies)

    tools = registry.get_tools_for_agent("UnknownAgent")
    assert tools == []  # Should return empty list for unknown agent


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
