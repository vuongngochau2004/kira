"""Tools layer for LangChain agent integration."""

from tools.retrieval_tools import (
    init_retrieval_tools,
    dense_retrieve,
    bm25_retrieve,
    hybrid_retrieve,
    query_expansion_tool,
    hybrid_retrieve_with_expansion,
    retrieve_with_rerank,
    format_documents_for_context,
)
from tools.ingestion_tools import (
    init_ingestion_tools,
    extract_text_tool,
    clean_text_tool,
    chunk_text_tool,
    embed_chunks_tool,
)
from tools.reranking_tools import (
    init_reranking_tools,
    llm_rerank,
    score_and_rerank,
)
from tools.llm_generation_tools import (
    init_llm_tools,
    generate_tool,
    chat_with_history_tool,
    generate_with_tools_tool,
    estimate_tokens_tool,
    validate_prompt_tool,
)
from tools.quality_tools import (
    init_quality_tools,
    critique_response_tool,
    verify_facts_tool,
    combined_quality_assessment,
    calculate_quality_metrics,
)
from tools.tool_registry import (
    ToolRegistry,
    get_tool_registry,
    initialize_tool_registry,
    get_tools_for_langgraph,
)

__all__ = [
    # Retrieval tools
    "init_retrieval_tools",
    "dense_retrieve",
    "bm25_retrieve",
    "hybrid_retrieve",
    "query_expansion_tool",
    "hybrid_retrieve_with_expansion",
    "retrieve_with_rerank",
    "format_documents_for_context",
    # Ingestion tools
    "init_ingestion_tools",
    "extract_text_tool",
    "clean_text_tool",
    "chunk_text_tool",
    "embed_chunks_tool",
    # Reranking tools
    "init_reranking_tools",
    "llm_rerank",
    "score_and_rerank",
    # LLM generation tools
    "init_llm_tools",
    "generate_tool",
    "chat_with_history_tool",
    "generate_with_tools_tool",
    "estimate_tokens_tool",
    "validate_prompt_tool",
    # Quality assessment tools (4-agent architecture)
    "init_quality_tools",
    "critique_response_tool",
    "verify_facts_tool",
    "combined_quality_assessment",
    "calculate_quality_metrics",
    # Tool registry (4-agent architecture)
    "ToolRegistry",
    "get_tool_registry",
    "initialize_tool_registry",
    "get_tools_for_langgraph",
]
