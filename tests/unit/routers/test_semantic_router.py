"""Unit tests for semantic router."""

import pytest

from src.agents.routers.semantic import (
    KIRASemanticRouter,
    get_conversational_route,
    get_rag_legal_route,
)


class TestSemanticRouter:
    """Test semantic router functionality."""

    @pytest.fixture
    def semantic_router(self):
        """Semantic router instance for testing."""
        return KIRASemanticRouter(threshold=0.75)

    def test_conversational_route_greeting(self, semantic_router):
        """Test conversational greeting query routing."""
        result = semantic_router.route("xin chào")
        assert result is not None
        assert result["router_name"] == "ConversationalRouter"
        assert result["score"] > 0.75
        assert result["method"] == "semantic"

    def test_conversational_route_about_bot(self, semantic_router):
        """Test conversational query about bot."""
        result = semantic_router.route("bạn tên gì")
        assert result is not None
        assert result["router_name"] == "ConversationalRouter"
        assert result["score"] > 0.75

    def test_conversational_route_gratitude(self, semantic_router):
        """Test conversational gratitude query routing."""
        result = semantic_router.route("cảm ơn")
        assert result is not None
        assert result["router_name"] == "ConversationalRouter"
        assert result["score"] > 0.75

    def test_rag_legal_route_contract(self, semantic_router):
        """Test RAG legal contract query routing."""
        result = semantic_router.route("điều khoản hợp đồng")
        assert result is not None
        assert result["router_name"] == "RAGRouter"
        assert result["score"] > 0.75
        assert result["method"] == "semantic"

    def test_rag_legal_route_labor_law(self, semantic_router):
        """Test RAG legal labor law query routing."""
        result = semantic_router.route("quy định về lao động")
        assert result is not None
        assert result["router_name"] == "RAGRouter"
        assert result["score"] > 0.75

    def test_short_legal_query_contract(self, semantic_router):
        """Test short legal queries - contract (critical fix)."""
        # These were previously misrouted
        result = semantic_router.route("hợp đồng")
        assert result is not None
        assert result["router_name"] == "RAGRouter"
        assert result["score"] > 0.75

    def test_short_legal_query_law(self, semantic_router):
        """Test short legal queries - law (critical fix)."""
        result = semantic_router.route("luật")
        assert result is not None
        assert result["router_name"] == "RAGRouter"
        assert result["score"] > 0.75

    def test_short_legal_query_decree(self, semantic_router):
        """Test short legal queries - decree (critical fix)."""
        result = semantic_router.route("nghị định")
        assert result is not None
        assert result["router_name"] == "RAGRouter"
        assert result["score"] > 0.75

    def test_below_threshold_returns_none(self, semantic_router):
        """Test query below threshold returns None."""
        result = semantic_router.route("xyz123 meaningless query")
        # Should return None for queries below threshold
        assert result is None or result["score"] < 0.75

    def test_route_definitions_valid(self):
        """Test route definitions are valid."""
        conv_route = get_conversational_route()
        rag_route = get_rag_legal_route()

        assert conv_route.name == "conversational"
        assert len(conv_route.utterances) >= 20

        assert rag_route.name == "rag_legal"
        assert len(rag_route.utterances) >= 30

    def test_async_route_method(self, semantic_router):
        """Test async route method works."""
        import asyncio

        async def test_async():
            result = await semantic_router.route_async("xin chào")
            assert result is not None
            assert result["router_name"] == "ConversationalRouter"

        asyncio.run(test_async())

    def test_semantic_router_initialization(self):
        """Test semantic router initialization with custom threshold."""
        router = KIRASemanticRouter(threshold=0.8)
        assert router.threshold == 0.8
        assert router._router is not None

    def test_route_name_mapping(self, semantic_router):
        """Test route name mapping to KIRA router names."""
        assert "conversational" in semantic_router.route_name_mapping
        assert "rag_legal" in semantic_router.route_name_mapping
        assert semantic_router.route_name_mapping["conversational"] == "ConversationalRouter"
        assert semantic_router.route_name_mapping["rag_legal"] == "RAGRouter"
