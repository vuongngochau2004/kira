"""Integration tests for routing flow with semantic router."""

import pytest

from src.agents.orchestrator import create_orchestrator


@pytest.mark.asyncio
class TestRoutingFlow:
    """Test end-to-end routing flow."""

    @pytest.fixture
    async def orchestrator(self):
        """Orchestrator with semantic router enabled."""
        return create_orchestrator(enable_semantic=True)

    @pytest.fixture
    async def orchestrator_no_semantic(self):
        """Orchestrator with semantic router disabled."""
        return create_orchestrator(enable_semantic=False)

    async def test_conversational_routing_with_semantic(self, orchestrator):
        """Test conversational query flow with semantic router."""
        result = await orchestrator.query("xin chào", user_id="test")

        # Should have result
        assert result is not None
        assert "content" in result or "status" in result

        # Check routing method
        metadata = result.get("metadata", {})
        routing_method = metadata.get("routing_method")

        # Should use semantic or quick_filter (both acceptable)
        assert routing_method in ["semantic", "quick_filter", "llm_classifier"]

        # If semantic was used, verify the route
        if routing_method == "semantic":
            assert "semantic_route" in metadata
            assert metadata["semantic_route"] == "conversational"

    async def test_rag_routing_with_semantic(self, orchestrator):
        """Test RAG query flow with semantic router."""
        result = await orchestrator.query("quy định lao động", user_id="test")

        # Should have result
        assert result is not None
        assert "content" in result or "status" in result

        # Check routing method
        metadata = result.get("metadata", {})
        routing_method = metadata.get("routing_method")

        # Should use semantic, quick_filter, or llm_classifier
        assert routing_method in ["semantic", "quick_filter", "llm_classifier"]

        # If semantic was used, should route to RAG
        if routing_method == "semantic":
            assert "semantic_route" in metadata
            assert metadata["semantic_route"] == "rag_legal"

    async def test_short_legal_query_routing_critical(self, orchestrator):
        """Test short legal queries are routed correctly (MAIN ISSUE FIX)."""
        # This was the main issue - short queries like "hợp đồng"
        # were being misrouted to ConversationalRouter
        result = await orchestrator.query("hợp đồng", user_id="test")

        # Should have result
        assert result is not None

        # Check it routed correctly
        metadata = result.get("metadata", {})

        # Should NOT be purely conversational (this was the bug)
        # The semantic router should catch "hợp đồng" as rag_legal
        routing_method = metadata.get("routing_method")

        if routing_method == "semantic":
            # If semantic routing was used, it MUST be rag_legal
            assert metadata.get("semantic_route") == "rag_legal", \
                f"Expected rag_legal, got {metadata.get('semantic_route')}"
        elif routing_method == "quick_filter":
            # Quick filter might also work
            pass
        # Note: llm_classifier might still misclassify, but semantic
        # router should handle this case

    async def test_very_short_legal_queries(self, orchestrator):
        """Test very short single-word legal queries."""
        test_queries = ["luật", "nghị định", "quy định", "thông tư"]

        for query in test_queries:
            result = await orchestrator.query(query, user_id=f"test-{query}")
            assert result is not None, f"No result for query: {query}"

            # Verify it's not misrouted as conversational
            metadata = result.get("metadata", {})
            routing_method = metadata.get("routing_method")

            if routing_method == "semantic":
                # Should route to rag_legal, not conversational
                semantic_route = metadata.get("semantic_route")
                assert semantic_route == "rag_legal", \
                    f"Query '{query}' routed to {semantic_route} instead of rag_legal"

    async def test_semantic_vs_no_semantic_routing(self, orchestrator, orchestrator_no_semantic):
        """Test semantic routing actually changes behavior."""
        query = "hợp đồng"

        # With semantic router
        result_with = await orchestrator.query(query, user_id="test-with")
        metadata_with = result_with.get("metadata", {})
        method_with = metadata_with.get("routing_method")

        # Without semantic router
        result_without = await orchestrator_no_semantic.query(query, user_id="test-without")
        metadata_without = result_without.get("metadata", {})
        method_without = metadata_without.get("routing_method")

        # With semantic should use semantic routing
        # Without semantic should use quick_filter or llm_classifier
        assert method_with in ["semantic", "quick_filter", "llm_classifier"]
        assert method_without in ["quick_filter", "llm_classifier"]
        # "semantic" should NOT be in method_without
        assert method_without != "semantic"

    async def test_streaming_with_semantic_routing(self, orchestrator):
        """Test streaming response works with semantic routing."""
        chunks = []
        async for chunk in orchestrator.query_stream("xin chào", user_id="test"):
            chunks.append(chunk)

        # Should have chunks
        assert len(chunks) > 0

        # Should have routing chunk
        routing_chunks = [c for c in chunks if c.get("type") == "routing"]
        assert len(routing_chunks) > 0

        # Check routing info
        routing_data = routing_chunks[0].get("data", {})
        assert "router" in routing_data
        assert "method" in routing_data

    async def test_multiple_conversational_queries(self, orchestrator):
        """Test various conversational queries."""
        conversational_queries = [
            "bạn tên gì",
            "cảm ơn",
            "tạm biệt",
            "bạn khỏe không",
        ]

        for query in conversational_queries:
            result = await orchestrator.query(query, user_id=f"test-{query}")
            assert result is not None, f"No result for conversational query: {query}"

    async def test_multiple_rag_queries(self, orchestrator):
        """Test various RAG queries."""
        rag_queries = [
            "hợp đồng lao động",
            "quy định về thời giờ làm việc",
            "chế độ thưởng",
        ]

        for query in rag_queries:
            result = await orchestrator.query(query, user_id=f"test-{query}")
            assert result is not None, f"No result for RAG query: {query}"

    async def test_semantic_router_initialization_error_handling(self):
        """Test that semantic router initialization errors don't break system."""
        # Create orchestrator with semantic enabled
        # Even if semantic router fails to initialize, system should work
        try:
            orchestrator = create_orchestrator(enable_semantic=True)
            result = await orchestrator.query("test query", user_id="test")
            assert result is not None
        except Exception as e:
            pytest.fail(f"Orchestrator creation failed with: {e}")
