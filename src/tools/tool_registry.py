"""Tool registry and manager for 4-agent architecture.

Central place to manage all LangChain tools and initialize them
with proper dependencies for the agentic RAG system.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.tools import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all LangChain tools used in 4-agent architecture.

    Manages tool initialization, dependency injection, and provides
    organized access to tools by agent type.
    """

    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: Dict[str, Tool] = {}
        self._initialized = False

        # Dependency references
        self._qdrant_store = None
        self._bm25_index = None
        self._embedding_fn = None
        self._llm_client = None

    def initialize_dependencies(
        self,
        qdrant_store: Any = None,
        bm25_index: Any = None,
        embedding_fn: Any = None,
        llm_client: Any = None,
    ) -> None:
        """Initialize dependencies for all tools.

        Args:
            qdrant_store: Vector store instance
            bm25_index: BM25 index instance
            embedding_fn: Embedding function
            llm_client: LLM client
        """
        self._qdrant_store = qdrant_store
        self._bm25_index = bm25_index
        self._embedding_fn = embedding_fn
        self._llm_client = llm_client

        # Initialize all tool modules
        from tools import (
            retrieval_tools,
            reranking_tools,
            llm_generation_tools,
            quality_tools,
        )

        retrieval_tools.init_retrieval_tools(
            qdrant_store=qdrant_store,
            bm25_index=bm25_index,
            embedding_fn=embedding_fn,
            llm_client=llm_client,
        )

        reranking_tools.init_reranking_tools(llm_client=llm_client)
        llm_generation_tools.init_llm_tools(llm_client=llm_client)
        quality_tools.init_quality_tools(llm_client=llm_client)

        self._initialized = True
        logger.info("Tool dependencies initialized")

    def register_all_tools(self) -> None:
        """Register all available tools from all modules."""
        if not self._initialized:
            raise RuntimeError("Must initialize dependencies before registering tools")

        from tools import (
            retrieval_tools,
            reranking_tools,
            llm_generation_tools,
            quality_tools,
        )

        # Retrieval tools
        self._tools["dense_retrieve"] = retrieval_tools.dense_retrieve
        self._tools["bm25_retrieve"] = retrieval_tools.bm25_retrieve
        self._tools["hybrid_retrieve"] = retrieval_tools.hybrid_retrieve
        self._tools["query_expansion_tool"] = retrieval_tools.query_expansion_tool
        self._tools["hybrid_retrieve_with_expansion"] = retrieval_tools.hybrid_retrieve_with_expansion
        self._tools["retrieve_with_rerank"] = retrieval_tools.retrieve_with_rerank
        self._tools["format_documents_for_context"] = retrieval_tools.format_documents_for_context

        # Reranking tools
        self._tools["llm_rerank"] = reranking_tools.llm_rerank
        self._tools["score_and_rerank"] = reranking_tools.score_and_rerank

        # LLM generation tools
        self._tools["generate_tool"] = llm_generation_tools.generate_tool
        self._tools["chat_with_history_tool"] = llm_generation_tools.chat_with_history_tool
        self._tools["generate_with_tools_tool"] = llm_generation_tools.generate_with_tools_tool
        self._tools["estimate_tokens_tool"] = llm_generation_tools.estimate_tokens_tool
        self._tools["validate_prompt_tool"] = llm_generation_tools.validate_prompt_tool

        # Quality assessment tools
        self._tools["critique_response_tool"] = quality_tools.critique_response_tool
        self._tools["verify_facts_tool"] = quality_tools.verify_facts_tool
        self._tools["combined_quality_assessment"] = quality_tools.combined_quality_assessment
        self._tools["calculate_quality_metrics"] = quality_tools.calculate_quality_metrics

        logger.info(f"Registered {len(self._tools)} tools")

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get a specific tool by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)

    def get_retrieval_tools(self) -> List[Tool]:
        """Get all retrieval-related tools for RetrievalAgent.

        Returns:
            List of retrieval tools
        """
        retrieval_tool_names = [
            "dense_retrieve",
            "bm25_retrieve",
            "hybrid_retrieve",
            "query_expansion_tool",
            "hybrid_retrieve_with_expansion",
            "retrieve_with_rerank",
            "format_documents_for_context",
        ]
        return [self._tools[name] for name in retrieval_tool_names if name in self._tools]

    def get_generation_tools(self) -> List[Tool]:
        """Get all generation-related tools for GenerationAgent.

        Returns:
            List of generation tools
        """
        generation_tool_names = [
            "generate_tool",
            "chat_with_history_tool",
            "generate_with_tools_tool",
            "estimate_tokens_tool",
            "validate_prompt_tool",
        ]
        return [self._tools[name] for name in generation_tool_names if name in self._tools]

    def get_quality_tools(self) -> List[Tool]:
        """Get all quality assessment tools for QualityAgent.

        Returns:
            List of quality tools
        """
        quality_tool_names = [
            "critique_response_tool",
            "verify_facts_tool",
            "combined_quality_assessment",
            "calculate_quality_metrics",
        ]
        return [self._tools[name] for name in quality_tool_names if name in self._tools]

    def get_reranking_tools(self) -> List[Tool]:
        """Get all reranking tools.

        Returns:
            List of reranking tools
        """
        reranking_tool_names = [
            "llm_rerank",
            "score_and_rerank",
        ]
        return [self._tools[name] for name in reranking_tool_names if name in self._tools]

    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools.

        Returns:
            List of all tools
        """
        return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        """Get names of all registered tools.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_tools_for_agent(self, agent_type: str) -> List[Tool]:
        """Get tools appropriate for a specific agent type.

        Args:
            agent_type: Type of agent (RetrievalAgent, GenerationAgent, QualityAgent, OrchestratorAgent)

        Returns:
            List of tools for the agent
        """
        if agent_type == "RetrievalAgent":
            return self.get_retrieval_tools()
        elif agent_type == "GenerationAgent":
            return self.get_generation_tools() + self.get_retrieval_tools()
        elif agent_type == "QualityAgent":
            return self.get_quality_tools()
        elif agent_type == "OrchestratorAgent":
            # Orchestrator needs access to all tools for routing decisions
            return self.get_all_tools()
        else:
            logger.warning(f"Unknown agent type: {agent_type}")
            return []

    def list_tools_by_category(self) -> Dict[str, List[str]]:
        """List all tools organized by category.

        Returns:
            Dict mapping category names to tool names
        """
        return {
            "retrieval": [name for name in self.get_retrieval_tools() if hasattr(name, 'name')],
            "generation": [name for name in self.get_generation_tools() if hasattr(name, 'name')],
            "quality": [name for name in self.get_quality_tools() if hasattr(name, 'name')],
            "reranking": [name for name in self.get_reranking_tools() if hasattr(name, 'name')],
        }


# Global tool registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def initialize_tool_registry(
    qdrant_store: Any = None,
    bm25_index: Any = None,
    embedding_fn: Any = None,
    llm_client: Any = None,
) -> ToolRegistry:
    """Initialize the global tool registry with dependencies.

    This is the main entry point for setting up tools for the 4-agent system.

    Args:
        qdrant_store: Vector store instance
        bm25_index: BM25 index instance
        embedding_fn: Embedding function
        llm_client: LLM client

    Returns:
        Initialized ToolRegistry instance

    Example:
        >>> registry = initialize_tool_registry(
        ...     qdrant_store=qdrant_client,
        ...     bm25_index=bm25_instance,
        ...     embedding_fn=embed_text,
        ...     llm_client=llm
        ... )
        >>> retrieval_tools = registry.get_retrieval_tools()
    """
    registry = get_tool_registry()
    registry.initialize_dependencies(
        qdrant_store=qdrant_store,
        bm25_index=bm25_index,
        embedding_fn=embedding_fn,
        llm_client=llm_client,
    )
    registry.register_all_tools()
    return registry


def get_tools_for_langgraph(agent_type: str) -> List[Tool]:
    """Get tools formatted for LangGraph agent binding.

    Args:
        agent_type: Type of agent

    Returns:
        List of tools ready for LangGraph .bind_tools()
    """
    registry = get_tool_registry()
    return registry.get_tools_for_agent(agent_type)


__all__ = [
    "ToolRegistry",
    "get_tool_registry",
    "initialize_tool_registry",
    "get_tools_for_langgraph",
]
