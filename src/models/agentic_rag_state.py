"""
RAGState Schema Definitions for Agentic RAG Architecture

This module defines all state schemas used in the LangGraph-based Agentic RAG system.
Follows Pydantic v2 patterns with strict type checking and validation.
"""

from typing import Any, Dict, List, Optional, TypedDict
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing_extensions import Annotated

from models.documents import DocumentResponse


# ============================================================================
# Base Models
# ============================================================================

class Citation(BaseModel):
    """Citation information for retrieved documents."""
    filename: str = Field(..., description="Source filename")
    page_number: Optional[int] = Field(None, description="Page number in source document")
    text: str = Field(..., description="Cited text excerpt")
    doc_index: Optional[int] = Field(None, description="Document index in response")
    score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance score")
    chunk_index: Optional[int] = Field(None, description="Chunk index within document")


# ============================================================================
# Enums
# ============================================================================

class AgentStatus(str, Enum):
    """Status of agent execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RetrievalStrategy(str, Enum):
    """Retrieval strategy types"""
    DENSE = "dense"
    BM25 = "bm25"
    HYBRID = "hybrid"
    EXPANSION = "expansion"


class QualityScore(str, Enum):
    """Quality assessment levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    FAILED = "failed"


# ============================================================================
# Base Models
# ============================================================================

class AgentResult(BaseModel):
    """Base result from any agent"""
    agent_name: str = Field(..., description="Name of the agent that produced this result")
    status: AgentStatus = Field(default=AgentStatus.COMPLETED, description="Execution status")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    model_config = ConfigDict(use_enum_values=True)


class RetrievalMetadata(BaseModel):
    """Metadata for retrieval operations"""
    strategy: RetrievalStrategy = Field(..., description="Retrieval strategy used")
    total_results: int = Field(..., description="Total number of results retrieved")
    query_expansions: List[str] = Field(default_factory=list, description="Query expansion terms")
    search_time_ms: float = Field(..., description="Search execution time")
    index_size: Optional[int] = Field(None, description="Size of the index searched")

    model_config = ConfigDict(use_enum_values=True)


class DocumentWithScore(BaseModel):
    """Document with relevance score"""
    doc_id: UUID = Field(..., description="Document ID")
    content: str = Field(..., description="Document content/text")
    filename: str = Field(..., description="Source filename")
    page_number: Optional[int] = Field(None, description="Page number in source document")
    chunk_index: Optional[int] = Field(None, description="Chunk index within document")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional document metadata")

    @field_validator('score')
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Ensure score is between 0 and 1"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Score must be between 0 and 1")
        return v


class RerankingResult(BaseModel):
    """Result from reranking process"""
    original_score: float = Field(..., description="Original retrieval score")
    reranked_score: float = Field(..., description="Score after reranking")
    score_delta: float = Field(..., description="Change in score")
    rank_position: int = Field(..., ge=1, description="Final rank position (1-indexed)")
    reranker_model: str = Field(..., description="Reranker model used")


class CritiqueResult(BaseModel):
    """Result from critique agent"""
    quality_level: QualityScore = Field(..., description="Overall quality assessment")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in quality assessment")
    issues: List[str] = Field(default_factory=list, description="List of identified issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    should_regenerate: bool = Field(default=False, description="Whether regeneration is recommended")

    model_config = ConfigDict(use_enum_values=True)


class VerificationResult(BaseModel):
    """Result from verification agent"""
    is_verified: bool = Field(..., description="Whether the response passed verification")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Verification confidence")
    factual_consistency: float = Field(..., ge=0.0, le=1.0, description="Factual consistency score")
    citation_accuracy: float = Field(..., ge=0.0, le=1.0, description="Citation accuracy score")
    reasoning_quality: float = Field(..., ge=0.0, le=1.0, description="Quality of reasoning")
    verification_checks: List[str] = Field(default_factory=list, description="List of checks performed")


# ============================================================================
# Main RAGState (TypedDict for LangGraph)
# ============================================================================

class RAGState(TypedDict):
    """
    Main state object passed between agents in the LangGraph.

    This TypedDict is used by LangGraph for state management.
    All agents receive this state and can modify it.

    4-AGENT ARCHITECTURE:
        1. RetrievalAgent - Merges query refinement, retrieval, and reranking
        2. GenerationAgent - LLM generation with citations
        3. QualityAgent - Merges critique and verification
        4. OrchestratorAgent - Coordination, routing, and decision-making

    State Flow:
        orchestrator -> retrieval_agent -> generation_agent ->
        quality_agent -> orchestrator (final decision) -> END
    """
    # Input fields (provided by user)
    query: str  # Original user query
    user_id: str  # User ID for personalization
    conversation_id: Optional[UUID]  # Conversation context (optional)

    # Orchestrator state - NEW for 4-agent architecture
    orchestrator_state: Dict[str, Any]  # Routing decisions, agent selection, flow control
    routing_decision: Optional[str]  # Which agent/route to use next
    agent_pipeline: List[str]  # Ordered list of agents to execute

    # Retrieval agent output - Merges query refinement + retrieval + reranking
    retrieval_agent_output: Dict[str, Any]  # Combined output from retrieval agent
    # Includes: refined_queries, retrieved_docs, reranked_docs, metadata

    # Generation agent output
    generated_response: str  # Final LLM-generated response
    generation_metadata: Dict[str, Any]  # LLM metadata (model, tokens, etc.)

    # Quality agent output - Merges critique + verification
    quality_agent_output: Dict[str, Any]  # Combined output from quality agent
    # Includes: quality_score, critique, verification, suggestions

    # Final output
    final_response: str  # Final response after all processing
    final_citations: List[Citation]  # Final citation list
    is_final: bool  # Whether this is the final response

    # Execution tracking
    agent_results: List[AgentResult]  # Results from each agent
    current_agent: str  # Currently executing agent
    total_execution_time_ms: float  # Total execution time

    # Error handling
    errors: List[str]  # Accumulated errors
    should_fallback: bool  # Whether to fall back to simple RAG
    fallback_reason: Optional[str]  # Reason for fallback


# ============================================================================
# Pydantic Models for Validation
# ============================================================================

class RAGStateValidator(BaseModel):
    """
    Pydantic version of RAGState for validation.
    Used to validate state before/after agent execution.
    """
    query: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(..., min_length=1)
    conversation_id: Optional[UUID] = None

    # Orchestrator state
    orchestrator_state: Dict[str, Any] = Field(default_factory=dict)
    routing_decision: Optional[str] = None
    agent_pipeline: List[str] = Field(default_factory=list)

    # Retrieval agent output
    retrieval_agent_output: Dict[str, Any] = Field(default_factory=dict)

    # Generation
    generated_response: str = Field(default="")
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)

    # Quality agent output
    quality_agent_output: Dict[str, Any] = Field(default_factory=dict)

    final_response: str = Field(default="")
    final_citations: List[Citation] = Field(default_factory=list)
    is_final: bool = Field(default=False)

    agent_results: List[AgentResult] = Field(default_factory=list)
    current_agent: str = Field(default="")
    total_execution_time_ms: float = Field(default=0.0, ge=0.0)

    errors: List[str] = Field(default_factory=list)
    should_fallback: bool = Field(default=False)
    fallback_reason: Optional[str] = None

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is not empty and reasonable length"""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        if len(v) > 2000:
            raise ValueError("Query too long (max 2000 characters)")
        return v.strip()

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user_id"""
        if not v or not v.strip():
            raise ValueError("User ID cannot be empty")
        return v

    @field_validator('agent_pipeline')
    @classmethod
    def validate_pipeline(cls, v: List[str]) -> List[str]:
        """Validate agent pipeline contains valid agents"""
        valid_agents = {"RetrievalAgent", "GenerationAgent", "QualityAgent", "OrchestratorAgent"}
        for agent in v:
            if agent not in valid_agents:
                raise ValueError(f"Invalid agent name: {agent}")
        return v


# ============================================================================
# Configuration Models
# ============================================================================

class AgentConfig(BaseModel):
    """Base configuration for agents"""
    enabled: bool = Field(default=True, description="Whether agent is enabled")
    timeout_ms: int = Field(default=30000, ge=1000, le=300000, description="Timeout in milliseconds")
    max_retries: int = Field(default=1, ge=0, le=5, description="Maximum retry attempts")
    log_level: str = Field(default="INFO", description="Logging level")


class OrchestratorAgentConfig(AgentConfig):
    """
    Configuration for OrchestratorAgent - NEW in 4-agent architecture.

    The OrchestratorAgent is responsible for:
    - Routing decisions (which agent to call next)
    - Flow control (when to proceed, retry, or fallback)
    - Agent coordination (managing the pipeline)
    - Quality gate enforcement (deciding when response is good enough)
    """
    enable_routing: bool = Field(default=True, description="Enable intelligent routing")
    enable_flow_control: bool = Field(default=True, description="Enable flow control")
    quality_gate_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum quality to proceed")
    max_pipeline_iterations: int = Field(default=3, ge=1, le=10, description="Max iterations through pipeline")
    enable_adaptive_routing: bool = Field(default=True, description="Enable adaptive routing based on query type")


class RetrievalAgentConfig(AgentConfig):
    """
    Configuration for RetrievalAgent - Merged in 4-agent architecture.

    The RetrievalAgent now handles:
    - Query refinement (formerly QueryRefinerAgent)
    - Document retrieval (original functionality)
    - Reranking (formerly RerankingAgent)

    This consolidation reduces overhead and improves coordination.
    """
    # Query refinement settings (merged from QueryRefinerAgent)
    expansion_count: int = Field(default=3, ge=1, le=10, description="Number of query expansions")
    use_llm_expansion: bool = Field(default=True, description="Use LLM for query expansion")
    use_synonym_expansion: bool = Field(default=True, description="Use synonym expansion")
    preserve_original: bool = Field(default=True, description="Include original query in results")

    # Retrieval settings
    top_k: int = Field(default=10, ge=1, le=100, description="Number of documents to retrieve")
    strategies: List[RetrievalStrategy] = Field(
        default=[RetrievalStrategy.HYBRID],
        description="Retrieval strategies to use"
    )
    min_score_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum relevance score")

    # Reranking settings (merged from RerankingAgentConfig)
    enable_reranking: bool = Field(default=True, description="Enable reranking within retrieval agent")
    rerank_top_k: int = Field(default=5, ge=1, le=50, description="Number of documents to keep after reranking")
    reranker_model: str = Field(default="cross-encoder", description="Reranker model to use")
    rerank_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum reranked score")


class GenerationAgentConfig(AgentConfig):
    """
    Configuration for GenerationAgent - Same as before.

    The GenerationAgent handles:
    - LLM response generation
    - Citation extraction and formatting
    - Response streaming
    """
    model: str = Field(default="glm-4.5", description="LLM model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: int = Field(default=2000, ge=100, le=8000, description="Maximum tokens to generate")
    stream_response: bool = Field(default=True, description="Enable streaming response")
    include_citations: bool = Field(default=True, description="Include citations in response")
    citation_style: str = Field(default="markdown", description="Citation format (markdown, json, html)")


class QualityAgentConfig(AgentConfig):
    """
    Configuration for QualityAgent - Merged in 4-agent architecture.

    The QualityAgent now handles:
    - Quality assessment (formerly CritiqueAgent)
    - Verification and fact-checking (formerly VerificationAgent)
    - Improvement suggestions
    - Final approval decision

    This consolidation provides unified quality control.
    """
    # Critique settings (merged from CritiqueAgentConfig)
    enable_critique: bool = Field(default=True, description="Enable critique within quality agent")
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum quality threshold")
    critique_model: str = Field(default="glm-4.5", description="Model for critique")

    # Verification settings (merged from VerificationAgentConfig)
    enable_verification: bool = Field(default=True, description="Enable verification within quality agent")
    verification_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum verification score")
    verify_facts: bool = Field(default=True, description="Verify factual consistency")
    verify_citations: bool = Field(default=True, description="Verify citation accuracy")

    # Unified quality settings
    max_iterations: int = Field(default=2, ge=0, le=5, description="Maximum quality check iterations")
    require_both_checks: bool = Field(default=False, description="Require both critique AND verification to pass")
    weight_critique: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight of critique in final score")
    weight_verification: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight of verification in final score")


class AgenticRAGConfig(BaseModel):
    """
    Complete configuration for Agentic RAG system (4-agent architecture).

    This config controls all aspects of the agentic RAG pipeline.
    Individual agents can be enabled/disabled and tuned here.

    4-AGENT ARCHITECTURE:
    1. OrchestratorAgent - Coordination and routing
    2. RetrievalAgent - Query refinement + retrieval + reranking
    3. GenerationAgent - LLM generation with citations
    4. QualityAgent - Critique + verification
    """
    # Global settings
    enable_fallback: bool = Field(default=True, description="Enable fallback to simple RAG")
    fallback_timeout_ms: int = Field(default=45000, ge=5000, description="Timeout before fallback")
    max_total_time_ms: int = Field(default=60000, ge=10000, description="Maximum total execution time")

    # Agent configurations (4-agent architecture)
    orchestrator: OrchestratorAgentConfig = Field(default_factory=OrchestratorAgentConfig)
    retrieval: RetrievalAgentConfig = Field(default_factory=RetrievalAgentConfig)
    generation: GenerationAgentConfig = Field(default_factory=GenerationAgentConfig)
    quality: QualityAgentConfig = Field(default_factory=QualityAgentConfig)

    # Feature flags (updated for 4-agent architecture)
    enable_orchestrator: bool = Field(default=True, description="Enable orchestrator agent")
    enable_retrieval: bool = Field(default=True, description="Enable retrieval agent")
    enable_generation: bool = Field(default=True, description="Enable generation agent")
    enable_quality: bool = Field(default=True, description="Enable quality agent")

    # Logging
    log_agent_execution: bool = Field(default=True, description="Log detailed agent execution")
    log_intermediate_results: bool = Field(default=False, description="Log intermediate results")

    model_config = ConfigDict(use_enum_values=True)


# ============================================================================
# Helper Functions
# ============================================================================

def create_initial_state(
    query: str,
    user_id: str,
    conversation_id: Optional[UUID] = None
) -> RAGState:
    """
    Create initial RAGState for starting the agentic RAG pipeline.

    Args:
        query: User's query
        user_id: User ID
        conversation_id: Optional conversation ID for context

    Returns:
        Initialized RAGState dictionary with 4-agent architecture
    """
    return {
        "query": query,
        "user_id": user_id,
        "conversation_id": conversation_id,

        # Orchestrator state
        "orchestrator_state": {
            "routing_history": [],
            "flow_decisions": [],
            "iteration_count": 0
        },
        "routing_decision": None,
        "agent_pipeline": ["OrchestratorAgent", "RetrievalAgent", "GenerationAgent", "QualityAgent"],

        # Retrieval agent output (merged from query_refiner + retrieval + reranking)
        "retrieval_agent_output": {
            "refined_queries": [],
            "retrieved_docs": [],
            "reranked_docs": [],
            "metadata": RetrievalMetadata(
                strategy=RetrievalStrategy.HYBRID,
                total_results=0,
                search_time_ms=0.0
            )
        },

        # Generation
        "generated_response": "",
        "generation_metadata": {},

        # Quality agent output (merged from critique + verification)
        "quality_agent_output": {
            "quality_score": 0.0,
            "critique": None,
            "verification": None,
            "suggestions": [],
            "should_regenerate": False
        },

        # Final output
        "final_response": "",
        "final_citations": [],
        "is_final": False,

        # Execution tracking
        "agent_results": [],
        "current_agent": "",
        "total_execution_time_ms": 0.0,

        # Error handling
        "errors": [],
        "should_fallback": False,
        "fallback_reason": None
    }


def validate_state(state: RAGState) -> RAGStateValidator:
    """
    Validate RAGState using Pydantic model.

    Args:
        state: RAGState to validate

    Returns:
        Validated RAGStateValidator instance

    Raises:
        ValidationError: If state is invalid
    """
    return RAGStateValidator(**state)


def create_agent_result(
    agent_name: str,
    status: AgentStatus,
    execution_time_ms: float,
    metadata: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> AgentResult:
    """
    Create an AgentResult object.

    Args:
        agent_name: Name of the agent
        status: Execution status
        execution_time_ms: Execution time in milliseconds
        metadata: Additional metadata
        error_message: Error message if failed

    Returns:
        AgentResult instance
    """
    return AgentResult(
        agent_name=agent_name,
        status=status,
        execution_time_ms=execution_time_ms,
        metadata=metadata or {},
        error_message=error_message
    )


# ============================================================================
# State Update Helpers
# ============================================================================

def update_state_with_agent_result(
    state: RAGState,
    agent_result: AgentResult
) -> RAGState:
    """Add agent result to state"""
    state["agent_results"].append(agent_result)
    return state


def update_state_with_error(
    state: RAGState,
    error_message: str
) -> RAGState:
    """Add error to state"""
    state["errors"].append(error_message)
    return state


def mark_agent_start(state: RAGState, agent_name: str) -> RAGState:
    """Mark the start of an agent's execution"""
    state["current_agent"] = agent_name
    return state


def calculate_total_time(state: RAGState) -> RAGState:
    """Calculate total execution time from agent results"""
    total_time = sum(
        result.execution_time_ms or 0.0
        for result in state["agent_results"]
    )
    state["total_execution_time_ms"] = total_time
    return state


# ============================================================================
# 4-Agent Architecture Helper Functions
# ============================================================================

def update_orchestrator_routing(
    state: RAGState,
    routing_decision: str,
    metadata: Optional[Dict[str, Any]] = None
) -> RAGState:
    """
    Update orchestrator routing decision and history.

    Args:
        state: Current RAGState
        routing_decision: Next agent/route to take
        metadata: Optional routing metadata

    Returns:
        Updated RAGState
    """
    state["routing_decision"] = routing_decision
    state["orchestrator_state"]["routing_history"].append({
        "decision": routing_decision,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {}
    })
    return state


def update_retrieval_output(
    state: RAGState,
    refined_queries: List[str],
    retrieved_docs: List[DocumentWithScore],
    reranked_docs: Optional[List[DocumentWithScore]] = None,
    metadata: Optional[RetrievalMetadata] = None
) -> RAGState:
    """
    Update retrieval agent output with combined retrieval results.

    Args:
        state: Current RAGState
        refined_queries: List of refined/expanded queries
        retrieved_docs: Documents retrieved from search
        reranked_docs: Documents after reranking (optional)
        metadata: Retrieval metadata

    Returns:
        Updated RAGState
    """
    state["retrieval_agent_output"]["refined_queries"] = refined_queries
    state["retrieval_agent_output"]["retrieved_docs"] = [doc.model_dump() for doc in retrieved_docs]
    state["retrieval_agent_output"]["reranked_docs"] = [doc.model_dump() for doc in (reranked_docs or retrieved_docs)]
    if metadata:
        state["retrieval_agent_output"]["metadata"] = metadata.model_dump()
    return state


def update_quality_output(
    state: RAGState,
    quality_score: float,
    critique: Optional[CritiqueResult] = None,
    verification: Optional[VerificationResult] = None,
    suggestions: Optional[List[str]] = None,
    should_regenerate: bool = False
) -> RAGState:
    """
    Update quality agent output with unified quality assessment.

    Args:
        state: Current RAGState
        quality_score: Overall quality score (0-1)
        critique: Optional critique result
        verification: Optional verification result
        suggestions: Optional improvement suggestions
        should_regenerate: Whether regeneration is recommended

    Returns:
        Updated RAGState
    """
    state["quality_agent_output"]["quality_score"] = quality_score
    state["quality_agent_output"]["critique"] = critique.model_dump() if critique else None
    state["quality_agent_output"]["verification"] = verification.model_dump() if verification else None
    state["quality_agent_output"]["suggestions"] = suggestions or []
    state["quality_agent_output"]["should_regenerate"] = should_regenerate
    return state


def get_retrieval_docs(state: RAGState) -> List[DocumentWithScore]:
    """
    Get retrieved documents from retrieval agent output.

    Args:
        state: Current RAGState

    Returns:
        List of DocumentWithScore objects
    """
    docs_data = state["retrieval_agent_output"].get("reranked_docs") or state["retrieval_agent_output"].get("retrieved_docs", [])
    return [DocumentWithScore(**doc) for doc in docs_data]


def get_refined_queries(state: RAGState) -> List[str]:
    """
    Get refined queries from retrieval agent output.

    Args:
        state: Current RAGState

    Returns:
        List of refined query strings
    """
    return state["retrieval_agent_output"].get("refined_queries", [])


def get_quality_score(state: RAGState) -> float:
    """
    Get overall quality score from quality agent output.

    Args:
        state: Current RAGState

    Returns:
        Quality score (0-1)
    """
    return state["quality_agent_output"].get("quality_score", 0.0)


def should_regenerate(state: RAGState) -> bool:
    """
    Check if response should be regenerated based on quality assessment.

    Args:
        state: Current RAGState

    Returns:
        True if regeneration is recommended
    """
    return state["quality_agent_output"].get("should_regenerate", False)


def increment_orchestrator_iteration(state: RAGState) -> RAGState:
    """
    Increment orchestrator iteration counter.

    Args:
        state: Current RAGState

    Returns:
        Updated RAGState
    """
    state["orchestrator_state"]["iteration_count"] = state["orchestrator_state"].get("iteration_count", 0) + 1
    return state
