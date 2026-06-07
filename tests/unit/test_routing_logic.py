"""Unit tests for query routing logic - ĐHBKĐN context."""

import pytest
from src.agents.routers.rag import RAGRouter
from src.agents.routers.conversational import ConversationalRouter
from src.agents.routers.registry import RouterRegistry


class TestRAGRouterCanHandle:
    """Test RAGRouter.can_handle() confidence scoring."""

    @pytest.mark.asyncio
    async def test_file_document_keywords_high_confidence(self):
        """Test file/document keywords return 0.95 confidence."""
        router = RAGRouter()

        # File indicators should give 0.95
        queries_with_file_keywords = [
            "Tìm trong file PDF về quy định",
            "Tài liệu quy chế đào tạo",
            "Tập tin Quyết định số 123",
            "Trích dẫn từ doc về tốt nghiệp",
            "Open file PDF để tra cứu",
        ]

        for query in queries_with_file_keywords:
            confidence = await router.can_handle(query)
            assert confidence == 0.95, f"Expected 0.95 for: '{query}', got {confidence}"

    @pytest.mark.asyncio
    async def test_document_indicators_medium_confidence(self):
        """Test document indicators return 0.7 confidence."""
        router = RAGRouter()

        # Document indicators should give 0.7
        queries_with_doc_indicators = [
            "Quy định về tuyển sinh là gì?",  # "quy định"
            "Tra cứu thủ tục xét tốt nghiệp",  # "tra cứu", "thủ tục"
            "Kiểm tra quy chế học bạ",  # "kiểm tra", "quy chế"
            "Tìm thông tin về học phí",  # "tìm", "về"
            "Cách nộp đơn xin học bút?",  # "cách"
        ]

        for query in queries_with_doc_indicators:
            confidence = await router.can_handle(query)
            assert confidence == 0.7, f"Expected 0.7 for: '{query}', got {confidence}"

    @pytest.mark.asyncio
    async def test_long_queries_medium_confidence(self):
        """Test longer queries (4+ words) return appropriate confidence.

        Note: Some long queries now match ĐHBKĐN keywords (added in refactor),
        resulting in 0.7 confidence instead of 0.5.
        """
        router = RAGRouter()

        # Long queries with doc indicators now return 0.7 (due to ĐHBKĐN keywords)
        doc_keyword_queries = [
            ("Hãy cho tôi biết về chương trình đào tạo", 0.7),  # matches "đào tạo"
            ("Tôi muốn tìm hiểu về quy trình xét tốt nghiệp", 0.7),  # matches "tốt nghiệp"
        ]

        for query, expected_confidence in doc_keyword_queries:
            confidence = await router.can_handle(query)
            assert confidence == expected_confidence, \
                f"Expected {expected_confidence} for: '{query}', got {confidence}"

        # Long queries without doc indicators still give 0.5
        # Note: "về" is a doc indicator, so any query with "về" returns 0.7
        # Using a generic conversational query without doc indicators
        long_query = "Tôi đang học và làm việc hàng ngày"
        confidence = await router.can_handle(long_query)
        assert confidence == 0.5, f"Expected 0.5 for: '{long_query}', got {confidence}"

    @pytest.mark.asyncio
    async def test_short_queries_low_confidence(self):
        """Test very short queries return 0.2 confidence."""
        router = RAGRouter()

        # Short queries give 0.2
        short_queries = [
            "Xin chào",  # 2 words
            "Cảm ơn",  # 2 words
            "Alo",  # 1 word
            "Chào",  # 1 word
        ]

        for query in short_queries:
            confidence = await router.can_handle(query)
            assert confidence == 0.2, f"Expected 0.2 for: '{query}', got {confidence}"

    @pytest.mark.asyncio
    async def test_xet_tot_nghiep_query_rag_confidence(self):
        """Test ĐHBKĐN-specific query: 'Điều kiện để xét tốt nghiệp là gì?'

        Expected: Should match 'quy định' → 0.7 confidence → RAG route
        """
        router = RAGRouter()
        query = "Điều kiện để xét tốt nghiệp là gì?"

        confidence = await router.can_handle(query)

        # Should match "quy định" → 0.7 confidence
        assert confidence == 0.7, f"Expected 0.7 for xet tốt nghiệp query, got {confidence}"
        assert confidence >= RouterRegistry.QUICK_THRESHOLD, \
            f"Confidence {confidence} should trigger Quick Filter (threshold: {RouterRegistry.QUICK_THRESHOLD})"


class TestConversationalRouterCanHandle:
    """Test ConversationalRouter.can_handle() confidence scoring."""

    @pytest.mark.asyncio
    async def test_greeting_keywords_high_confidence(self):
        """Test greeting keywords return high confidence."""
        router = ConversationalRouter()

        # Greetings should give high confidence
        greeting_queries = [
            "Xin chào",  # "xin chào"
            "Chào bạn",  # "chào"
            "Hello",  # "hello"
            "Hi",  # "hi"
            "Cảm ơn bạn",  # "cảm ơn"
            "Tạm biệt",  # "tạm biệt"
        ]

        for query in greeting_queries:
            confidence = await router.can_handle(query)
            # ConversationalRouter gives higher confidence for greetings
            assert confidence >= 0.8, f"Expected >= 0.8 for greeting: '{query}', got {confidence}"

    @pytest.mark.asyncio
    async def test_bot_questions_medium_confidence(self):
        """Test questions about bot return medium confidence."""
        router = ConversationalRouter()

        # Bot questions should give medium confidence
        bot_queries = [
            "Bạn tên là gì?",  # About bot name
            "Bạn làm được gì?",  # About bot capabilities
            "K.I.R.A là ai?",  # About bot identity
            "Cách sử dụng hệ thống",  # About how to use
        ]

        for query in bot_queries:
            confidence = await router.can_handle(query)
            # Should give at least medium confidence
            assert confidence >= 0.5, f"Expected >= 0.5 for bot question: '{query}', got {confidence}"


class TestRouterDecisionLogic:
    """Test routing decision logic for various query types."""

    @pytest.mark.asyncio
    async def test_rag_triggers_quick_filter(self):
        """Test that RAG queries trigger Quick Filter (confidence >= 0.7).

        These queries should bypass LLM classification and route directly to RAG.
        """
        rag_queries = [
            "Quy định về tuyển sinh là gì?",  # "quy định" → 0.7
            "Tra cứu thủ tục xét tốt nghiệp",  # "tra cứu", "thủ tục" → 0.7
            "Điều kiện để xét tốt nghiệp là gì?",  # "quy định" → 0.7
            "Tìm tài liệu về học bạ",  # "tìm", "tài liệu" → 0.7
            "Kiểm tra quy chế học phí",  # "kiểm tra", "quy chế" → 0.7
        ]

        router = RAGRouter()

        for query in rag_queries:
            confidence = await router.can_handle(query)
            assert confidence >= RouterRegistry.QUICK_THRESHOLD, \
                f"Query '{query}' with confidence {confidence} should trigger Quick Filter (threshold: {RouterRegistry.QUICK_THRESHOLD})"

    @pytest.mark.asyncio
    async def test_conversational_below_quick_threshold(self):
        """Test that conversational queries do NOT trigger Quick Filter.

        These queries should go to LLM classification.
        """
        conversational_queries = [
            "Xin chào",  # → 0.2 (RAG) but will lose to ConversationalRouter
            "Cảm ơn",  # → 0.2
            "Bạn tên là gì?",  # ConversationalRouter will win
        ]

        rag_router = RAGRouter()
        conv_router = ConversationalRouter()

        for query in conversational_queries:
            rag_confidence = await rag_router.can_handle(query)
            conv_confidence = await conv_router.can_handle(query)

            # Conversational should beat RAG for greetings
            assert conv_confidence > rag_confidence, \
                f"Conversational should beat RAG for '{query}' (conv: {conv_confidence}, rag: {rag_confidence})"

            # And not trigger Quick Filter for RAG
            assert rag_confidence < RouterRegistry.QUICK_THRESHOLD, \
                f"RAG confidence {rag_confidence} should NOT trigger Quick Filter for '{query}'"


class TestQuickFilterThreshold:
    """Test QUICK_THRESHOLD logic."""

    def test_quick_filter_threshold_value(self):
        """Test that QUICK_THRESHOLD is set to 0.7."""
        # This ensures queries with 0.7+ confidence trigger Quick Filter
        assert RouterRegistry.QUICK_THRESHOLD == 0.7, \
            f"QUICK_THRESHOLD should be 0.7, got {RouterRegistry.QUICK_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_exactly_threshold_triggers_quick_filter(self):
        """Test that confidence == 0.7 exactly triggers Quick Filter.

        This is important for queries like "Điều kiện để xét tốt nghiệp là gì?"
        which match "quy định" → 0.7 confidence.
        """
        router = RAGRouter()
        query = "Quy định về đào tạo"  # "quy định" → 0.7

        confidence = await router.can_handle(query)
        assert confidence == 0.7, f"Expected exactly 0.7, got {confidence}"
        assert confidence >= RouterRegistry.QUICK_THRESHOLD, \
            f"Confidence {confidence} should trigger Quick Filter (>= {RouterRegistry.QUICK_THRESHOLD})"


class TestDHBKDNQueryPatterns:
    """Test ĐHBKĐN-specific query patterns and their routing."""

    @pytest.mark.asyncio
    async def test_xet_tot_nghiep_queries_route_to_rag(self):
        """Test that 'xét tốt nghiệp' queries route to RAG."""
        router = RAGRouter()

        xet_tot_nghiep_queries = [
            "Điều kiện để xét tốt nghiệp là gì?",
            "Quy định về xét tốt nghiệp",
            "Thủ tục xét tốt nghiệp như thế nào?",
            "Hồ sơ xét tốt nghiệp bao gồm những gì?",
            "Căn cứ pháp lý xét tốt nghiệp",
        ]

        for query in xet_tot_nghiep_queries:
            confidence = await router.can_handle(query)
            assert confidence >= RouterRegistry.QUICK_THRESHOLD, \
                f"Xét tốt nghiệp query '{query}' should route to RAG (confidence: {confidence}, threshold: {RouterRegistry.QUICK_THRESHOLD})"

    @pytest.mark.asyncio
    async def test_tuyen_sinh_queries_route_to_rag(self):
        """Test that 'tuyển sinh' queries route to RAG."""
        router = RAGRouter()

        tuyen_sinh_queries = [
            "Quy định tuyển sinh là gì?",
            "Điều kiện tuyển sinh ĐHBKĐN",
            "Thủ tục nộp hồ sơ tuyển sinh",
            "Hồ sơ nhập học bao gồm gì?",
        ]

        for query in tuyen_sinh_queries:
            confidence = await router.can_handle(query)
            assert confidence >= RouterRegistry.QUICK_THRESHOLD, \
                f"Tuyển sinh query '{query}' should route to RAG (confidence: {confidence}, threshold: {RouterRegistry.QUICK_THRESHOLD})"

    @pytest.mark.asyncio
    async def test_hoc_ba_queries_route_to_rag(self):
        """Test that 'học bạ' queries route to RAG."""
        router = RAGRouter()

        hoc_ba_queries = [
            "Quy định về học bạ",
            "Điều kiện được miễn học bạ",
            "Thủ tục xét học bạ",
            "Học bạ toàn phần hay từng phần",
        ]

        for query in hoc_ba_queries:
            confidence = await router.can_handle(query)
            assert confidence >= RouterRegistry.QUICK_THRESHOLD, \
                f"Học bạ query '{query}' should route to RAG (confidence: {confidence}, threshold: {RouterRegistry.QUICK_THRESHOLD})"

    @pytest.mark.asyncio
    async def test_hoc_phi_queries_route_to_rag(self):
        """Test that 'học phí' queries route to RAG."""
        router = RAGRouter()

        hoc_phi_queries = [
            "Quy định học phí là gì?",
            "Mức học phí các ngành",
            "Thủ tục nộp học phí",
            "Miễn giảm học phí như thế nào?",
        ]

        for query in hoc_phi_queries:
            confidence = await router.can_handle(query)
            assert confidence >= RouterRegistry.QUICK_THRESHOLD, \
                f"Học phí query '{query}' should route to RAG (confidence: {confidence}, threshold: {RouterRegistry.QUICK_THRESHOLD})"

    @pytest.mark.asyncio
    async def test_quy_che_queries_route_to_rag(self):
        """Test that 'quy chế' queries route to RAG."""
        router = RAGRouter()

        quy_che_queries = [
            "Quy chế đào tạo ĐHBKĐN",
            "Quy chế sinh viên",
            "Quy chế thi cử",
            "Nội dung quy chế là gì?",
        ]

        for query in quy_che_queries:
            confidence = await router.can_handle(query)
            assert confidence >= RouterRegistry.QUICK_THRESHOLD, \
                f"Quy chế query '{query}' should route to RAG (confidence: {confidence}, threshold: {RouterRegistry.QUICK_THRESHOLD})"


class TestEdgeCases:
    """Test edge cases in routing logic."""

    @pytest.mark.asyncio
    async def test_empty_query_low_confidence(self):
        """Test empty query returns low confidence."""
        router = RAGRouter()

        confidence = await router.can_handle("")
        assert confidence <= 0.5, f"Empty query should have low confidence, got {confidence}"

    @pytest.mark.asyncio
    async def test_query_with_special_characters(self):
        """Test query with special characters works correctly."""
        router = RAGRouter()

        # Queries with special characters should still work
        special_queries = [
            "Quy định về học phí? Có miễn giảm không?",  # Question marks
            "Điều kiện: (1) Tốt nghiệp THPT, (2) Điểm trung bình",  # Parentheses, colons
            "Tra cứu \"Quy chế đào tạo\"",  # Quotes
        ]

        for query in special_queries:
            # Should not crash and should return valid confidence
            confidence = await router.can_handle(query)
            assert 0.0 <= confidence <= 1.0, f"Invalid confidence for special query: {confidence}"

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive."""
        router = RAGRouter()

        # Same keyword in different cases
        variants = [
            "Quy định về đào tạo",
            "QUY ĐỊNH về đào tạo",
            "quy định Về đào tạo",
            "QUY ĐỊNH VỀ ĐÀO TẠO",
        ]

        confidences = [await router.can_handle(q) for q in variants]
        # All should have same confidence (0.7 for "quy định")
        assert all(c == 0.7 for c in confidences), \
            f"Case variants should have same confidence 0.7, got {confidences}"

    @pytest.mark.asyncio
    async def test_multiple_keywords_highest_confidence(self):
        """Test query with multiple matching keywords gets appropriate confidence."""
        router = RAGRouter()

        # Query with both file and doc indicators
        query = "Tìm tài liệu PDF về quy định"
        confidence = await router.can_handle(query)

        # Should get file indicator confidence (0.95) since it matches "file"
        assert confidence == 0.95, \
            f"Query with multiple keywords should get highest confidence 0.95, got {confidence}"


class TestRouterComparison:
    """Test that routers are ranked correctly for each query type."""

    @pytest.mark.asyncio
    async def test_rag_vs_conversational_for_greeting(self):
        """Test that ConversationalRouter wins for greetings."""
        rag_router = RAGRouter()
        conv_router = ConversationalRouter()

        greetings = ["Xin chào", "Hello", "Cảm ơn"]

        for greeting in greetings:
            rag_conf = await rag_router.can_handle(greeting)
            conv_conf = await conv_router.can_handle(greeting)

            assert conv_conf > rag_conf, \
                f"For greeting '{greeting}': Convational ({conv_conf}) > RAG ({rag_conf})"

    @pytest.mark.asyncio
    async def test_rag_vs_conversational_for_document_query(self):
        """Test that RAGRouter wins for document queries."""
        rag_router = RAGRouter()
        conv_router = ConversationalRouter()

        doc_queries = [
            "Quy định về tuyển sinh",
            "Điều kiện xét tốt nghiệp",
            "Tra cứu tài liệu học phí",
        ]

        for query in doc_queries:
            rag_conf = await rag_router.can_handle(query)
            conv_conf = await conv_router.can_handle(query)

            assert rag_conf >= 0.7, \
                f"For doc query '{query}': RAG should have >= 0.7 confidence, got {rag_conf}"
            assert rag_conf > conv_conf, \
                f"For doc query '{query}': RAG ({rag_conf}) > Conversational ({conv_conf})"


class TestRouterRegistryQuickFilter:
    """Test RouterRegistry._quick_filter_router() logic."""

    @pytest.mark.asyncio
    async def test_quick_filter_returns_rag_router_for_doc_queries(self):
        """Test that _quick_filter_router returns RAGRouter for doc queries.

        This simulates Stage 1 of routing without needing full orchestrator.
        """
        # Setup: Register routers (this is what main.py does)
        from src.agents.routers.registry import RouterRegistry
        from src.agents.routers.rag import RAGRouter
        from src.agents.routers.conversational import ConversationalRouter

        RouterRegistry.register(RAGRouter(), "RAGRouter")
        RouterRegistry.register(ConversationalRouter(), "ConversationalRouter")

        # Test document queries
        doc_queries = [
            "Điều kiện để xét tốt nghiệp là gì?",
            "Quy định về tuyển sinh",
            "Tra cứu thủ tục học bạ",
        ]

        for query in doc_queries:
            # Simulate _quick_filter_router logic
            selected_router = None
            max_confidence = 0

            for router_name, router in RouterRegistry._routers.items():
                confidence = await router.can_handle(query)
                if confidence >= RouterRegistry.QUICK_THRESHOLD and confidence > max_confidence:
                    max_confidence = confidence
                    selected_router = router

            assert selected_router is not None, \
                f"Quick Filter should select a router for '{query}'"
            assert selected_router.get_name() == "RAGRouter", \
                f"Quick Filter should select RAGRouter for '{query}', got {selected_router.get_name()}"
            assert max_confidence >= RouterRegistry.QUICK_THRESHOLD, \
                f"Confidence {max_confidence} should meet threshold {RouterRegistry.QUICK_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_quick_filter_returns_none_for_greetings(self):
        """Test that greetings DO trigger Quick Filter to ConversationalRouter.

        Greetings are unambiguous conversational queries, so they should be
        quickly routed to ConversationalRouter via Quick Filter (Stage 1).

        Updated: After ConversationalRouter optimization, greetings return
        0.9 confidence, exceeding QUICK_THRESHOLD (0.7).
        """
        from src.agents.routers.registry import RouterRegistry
        from src.agents.routers.rag import RAGRouter
        from src.agents.routers.conversational import ConversationalRouter

        RouterRegistry.register(RAGRouter(), "RAGRouter")
        RouterRegistry.register(ConversationalRouter(), "ConversationalRouter")

        # Test greetings
        greetings = ["Xin chào", "Hello", "Cảm ơn"]

        for query in greetings:
            # Simulate _quick_filter_router logic
            selected_router = None
            max_confidence = 0

            for router_name, router in RouterRegistry._routers.items():
                confidence = await router.can_handle(query)
                if confidence >= RouterRegistry.QUICK_THRESHOLD and confidence > max_confidence:
                    max_confidence = confidence
                    selected_router = router

            # Greetings SHOULD trigger Quick Filter to ConversationalRouter
            assert selected_router is not None, \
                f"Quick Filter should select router for greeting '{query}' (max_conf: {max_confidence})"
            assert selected_router.get_name() == "ConversationalRouter", \
                f"Quick Filter should select ConversationalRouter for '{query}', got {selected_router.get_name()}"
            assert max_confidence >= RouterRegistry.QUICK_THRESHOLD, \
                f"Greeting '{query}' should have max_conf >= threshold, got {max_confidence}"


# Parameterized tests for query patterns
@pytest.mark.parametrize("query,expected_confidence,reason", [
    # File/document indicators → 0.95
    ("Tìm trong file PDF", 0.95, "file indicator"),
    ("Tài liệu quy định", 0.95, "tài liệu keyword"),

    # Document indicators → 0.7
    ("Quy định về tuyển sinh", 0.7, "quy định keyword"),
    ("Tra cứu thủ tục xét tốt nghiệp", 0.7, "tra cứu + thủ tục"),
    ("Điều kiện để xét tốt nghiệp là gì?", 0.7, "quy định keyword"),

    # Long queries with ĐHBKĐN keywords → 0.7
    ("Hãy cho tôi biết về chương trình đào tạo", 0.7, "đào tạo keyword"),
    ("Tôi muốn tìm hiểu về quy trình xét tốt nghiệp", 0.7, "tốt nghiệp keyword"),

    # Short queries → 0.2
    ("Xin chào", 0.2, "short greeting"),
    ("Cảm ơn", 0.2, "short thanks"),
])
@pytest.mark.asyncio
async def test_rag_confidence_scenarios(query, expected_confidence, reason):
    """Parameterized test for RAGRouter confidence scoring."""
    router = RAGRouter()
    confidence = await router.can_handle(query)

    assert confidence == expected_confidence, \
        f"For '{query}' ({reason}): expected {expected_confidence}, got {confidence}"


# Test main query from user
@pytest.mark.asyncio
async def test_user_main_query_xet_tot_nghiep():
    """Test the exact query from user: 'Điều kiện để xét tốt nghiệp là gì?'

    This is the critical test case for user's requirement.
    """
    router = RAGRouter()
    query = "Điều kiện để xét tốt nghiệp là gì?"

    confidence = await router.can_handle(query)

    # Should match "quy định" → 0.7 confidence
    assert confidence == 0.7, \
        f"Expected 0.7 for user's query, got {confidence}"

    # Should trigger Quick Filter (0.7 >= 0.7)
    assert confidence >= RouterRegistry.QUICK_THRESHOLD, \
        f"Query should trigger Quick Filter routing to RAG (confidence: {confidence}, threshold: {RouterRegistry.QUICK_THRESHOLD})"

    # Should route to RAG, not Conversational
    assert confidence >= 0.5, \
        "Query should be routed to RAG, not Conversational"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
