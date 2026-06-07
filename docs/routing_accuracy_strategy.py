"""Accuracy-focused routing strategy for ĐHBKĐN RAG system.

This module removes keyword-based Quick Filter bias and relies on:
1. Semantic routing (embedding-based)
2. LLM classification (intent-based)
3. Fallback to RAG (safe default)

This prioritizes accuracy over speed.
"""

# ============================================================================
# OPTION 1: REMOVE QUICK FILTER (Pure LLM Classification)
# ============================================================================

# In src/agents/routers/registry.py:

class RouterRegistry:
    """Registry for managing and routing queries to appropriate routers.

    Accuracy-focused routing strategy:
    1. Semantic Routing: Embedding-based similarity to known routes
    2. LLM Classification: Intent-based classification with ĐHBKĐN context
    3. Fallback: Default to RAGRouter (safe default)
    """

    # REMOVE Quick Filter, directly to LLM classification
    @classmethod
    async def route(
        cls,
        query: str,
        user_id: str | UUID = "default",
        conversation_history: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Route query using accuracy-focused strategy.

        Args:
            query: User query
            user_id: User ID for filtering
            conversation_history: Optional conversation history

        Returns:
            Response dict from selected router
        """
        t0 = time.perf_counter()

        # Stage 1: Semantic Routing (Embedding-based)
        if cls._semantic_router is not None:
            try:
                semantic_decision = await cls._semantic_router.route_async(query)

                if semantic_decision is not None and semantic_decision.get("score", 0) >= 0.7:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    router_name = semantic_decision["router_name"]
                    router = cls._routers.get(router_name)

                    if router is not None:
                        logger.debug(
                            f"Semantic routed to: {router_name} "
                            f"(score: {semantic_decision['score']:.2f})"
                        )

                        result = await router.handle(query, user_id, conversation_history=conversation_history)
                        result["latency_ms"] = latency_ms
                        result.setdefault("metadata", {})["routing_method"] = "semantic"
                        return result
            except Exception as e:
                logger.error(f"Semantic routing error: {e}")

        # Stage 2: LLM Classification (Primary routing)
        if cls._classifier is None:
            cls._classifier = QueryClassifier()

        logger.debug("Using LLM classifier for accurate routing...")
        classification = await cls._classifier.classify(query)

        # Stage 3: Intent-based Routing
        router_name = INTENT_TO_ROUTER.get(
            classification.intent,
            cls.DEFAULT_ROUTER  # Safe default
        )

        router = cls._routers.get(router_name)
        if not router:
            logger.warning(f"Router not found: {router_name}, using default")
            router = cls._routers.get(cls.DEFAULT_ROUTER)

        latency_ms = (time.perf_counter() - t0) * 1000

        try:
            result = await router.handle(query, user_id, conversation_history=conversation_history)
            result["latency_ms"] = latency_ms
            result.setdefault("metadata", {})["routing_method"] = "llm_classification"
            result.setdefault("metadata", {})["llm_confidence"] = classification.confidence
            result.setdefault("metadata", {})["llm_intent"] = classification.intent
            result.setdefault("metadata", {})["llm_reason"] = classification.reason

            # Log routing decision
            try:
                routing_logger.log_classification_decision(
                    query=query,
                    user_id=user_id,
                    router_selected=router_name,
                    confidence=classification.confidence,
                    intent=classification.intent,
                    reason=classification.reason,
                    latency_ms=latency_ms,
                    conversation_history=conversation_history,
                )
            except Exception as e:
                logger.error(f"Failed to log routing decision: {e}")

            return result

        except Exception as e:
            logger.error(f"Router {router_name} failed: {e}")
            latency_ms = (time.perf_counter() - t0) * 1000
            return {
                "content": f"Error processing query: {str(e)}",
                "latency_ms": latency_ms,
                "metadata": {"routing_method": "error", "error": str(e)}
            }


# ============================================================================
# OPTION 2: IMPROVED LLM CLASSIFIER PROMPT
# ============================================================================

# In src/agents/routers/classifier.py:

ROUTING_CLASSIFIER_PROMPT = """Bạn là classifier CHÍNH XÁC cho hệ thống ĐẠI HỌC BÁCH KHOA ĐÀ NẴNG (ĐHBKĐN).

Nhiệm vụ: Phân loại query vào RAG (hỏi đáp tài liệu) hoặc Conversational (chat).

**INPUT:** {query}

**CÁCH PHÂN LOẠI:**

1. **Xác định keywords:**
   - RAG keywords: điều, điều kiện, điều khoản, quy định, quy chế, quyết định,
                  thông báo, thủ tục, hồ sơ, tuyển sinh, good nghiệp, học bạ,
                  học phí, đào tạo, sinh viên, giảng dạy, nghiên cứu, khoa học
   - Conversational keywords: chào, xin chào, cảm ơn, tạm biệt, hello, hi,
                         bạn là ai, tên là gì, làm được gì, giúp gì, hướng dẫn

2. **Phân tích context:**
   - Nếu query bắt đầu bằng: "Cho tôi biết về", "Tìm hiểu về", "Cho tôi biết"
     → Phân tích tiếp: Nếu后面 có từ khóa RAG → RAG, nếu không → Conversational
   - Nếu query có cấu trúc: "Cách X", "Như thế nào X", "Làm sao X"
     → Nếu X là tài liệu/quy trình → RAG, nếu X là skill general → Conversational

3. **Xét độ tin cậy (Confidence):**
   - 0.9-1.0: Rất chắc (có rõ RAG keywords + context)
   - 0.7-0.9: Khá chắc (có RAG keywords)
   - 0.5-0.7: Chắc chắn một phần (cần phân tích thêm)
   - 0.3-0.5: Không chắc (cần LLM suy luận thêm)
   - 0.0-0.3: Rất không chắc (default)

**VÍ DỤ:**

*Example 1 (RAG):*
Query: "Điều kiện để xét good nghiệp là gì?"
- Keywords: "điều kiện", "xét", "good nghiệp" → RAG keywords
- Context: Hỏi về điều kiện/thủ tục → RAG query
→ Intent: RAG, Confidence: 0.95

*Example 2 (RAG):*
Query: "Số tín_only cần để good nghiệp là bao nhiêu?"
- Keywords: "tín_only", "good nghiệp" → RAG keywords
- Context: Hỏi về số lượng/thông số → RAG query
→ Intent: RAG, Confidence: 0.9

*Example 3 (Conversational):*
Query: "Xin chào, cho tôi hỏi về K.I.R.A"
- Keywords: "xin chào" → Conversational keyword
- Context: Chào hỏi + hỏi về bot → Conversational
→ Intent: Conversational, Confidence: 0.95

*Example 4 (Ambiguous):*
Query: "Cho tôi biết về quy trình good nghiệp"
- Keywords: "quy trình", "good nghiệp" → RAG keywords
- Context: "Cho tôi biết về" có thể là general inquiry
- BUT có RAG keywords nên thiên về RAG
→ Intent: RAG, Confidence: 0.7 (khá chắc)

*Example 5 (Ambiguous):*
Query: "Cho tôi biết cách sử dụng hệ thống"
- Keywords: "cách" → RAG keyword (có thể)
- Context: Hỏi về using system → Conversational
- "Cách sử dụng" có thể là hướng dẫn, không phải tra cứu tài liệu
→ Intent: Conversational, Confidence: 0.6 (thiên về Conversational)

**QUAN TRỌNG:**
- Mặc định thiên về RAG nếu có từ khóa RAG (safer default)
- Chỉ chọn Conversational khi RẤT chắc chắn là chat (0.8+ confidence)
- Nếu unsure (0.5-0.7), thiên về RAG (better to false positive RAG than false negative)

**TRẢ VỀ JSON:**
```json
{{
  "intent": "rag|conversational",
  "confidence": 0.0-1.0,
  "reason": "Lý do ngắn gọn: có keywords X, Y, Z; context là ABC"
}}
```
"""


# ============================================================================
# OPTION 3: KEEP KEYWORDS BUT LOWER THRESHOLD
# ============================================================================

# In src/agents/routers/registry.py:

class RouterRegistry:
    """Registry with lowered Quick Filter threshold.

    Still uses keyword matching but only for HIGH confidence (0.9+).
    Medium confidence (0.7-0.9) goes to LLM classification for accuracy.
    """

    # Lower threshold - only route on VERY HIGH confidence
    QUICK_THRESHOLD = 0.9  # Changed from 0.7

    @classmethod
    async def route(cls, query: str, user_id: str | UUID = "default",
                     conversation_history: list[dict] | None = None) -> dict[str, Any]:
        """Route with lowered threshold for accuracy."""

        t0 = time.perf_counter()

        # Stage 1: Quick Filter (Only 0.9+ confidence - VERY SURE)
        quick_router = await cls._quick_filter_router(query, user_id)
        if quick_router is not None:
            # Log and return
            ...

        # Stage 2: LLM Classification (Most queries go here)
        ...


# In src/agents/routers/rag.py:

class RAGRouter(BaseRouter):
    """RAG router with conservative keyword matching."""

    async def can_handle(self, query: str) -> float:
        """Conservative confidence scoring.

        Only returns 0.9+ for VERY OBVIOUS RAG queries.
        """
        query_lower = query.lower()

        # Very specific file/document patterns → 0.95
        if any(kw in query_lower for kw in [
            "tìm file", "tìm tài liệu", "mở file", "file pdf",
            "tra cứu quyết định", "tra cứu quy định", "tìm quy chế"
        ]):
            return 0.95

        # Generic doc indicators → 0.7 (NOT trigger Quick Filter)
        # Let LLM classifier decide
        if any(kw in query_lower for kw in [
            "tìm", "kiểm tra", "tra cứu", "theo", "trong", "về",
            "quy định", "thủ tục"
        ]):
            return 0.7  # Will NOT trigger Quick Filter (threshold 0.9)

        # Longer queries → 0.5 (NOT trigger Quick Filter)
        word_count = len(query.split())
        if word_count >= 4:
            return 0.5  # Will NOT trigger Quick Filter

        # Short queries → 0.2 (obviously conversational)
        return 0.2


# ============================================================================
# SEMANTIC ROUTING CONFIG (ĐHBKĐN Routes)
# ============================================================================

# In config/semantic_routes_dhdn.yaml:

semantic_routes:
  - name: "tuyen_sinh"
    router: "RAGRouter"
    queries:
      - "Điều kiện tuyển sinh"
      - "Quy trình tuyển sinh"
      - "Hồ sơ nhập học"
      - "Chỉ tiêu tuyển sinh"
      - "Phương thức tuyển sinh"
      - "Thời gian tuyển sinh"
      - "Nguyện vọng đăng ký"
    embedding_model: "vietnamese-embedding-v2"
    similarity_threshold: 0.75

  - name: "xet_tot_nghiep"
    router: "RAGRouter"
    queries:
      - "Quy trình xét good nghiệp"
      - "Điều kiện xét good nghiệp"
      - "Hội đồng xét good nghiệp"
      - "Thủ tục xét good nghiệp"
      - "Quy trình xét good nghiệp"
      - "Yêu cầu xét good nghiệp"
      - "Điều kiện được xét good nghiệp"
      - "Số tín_only cần"
      - "Học bạ toàn phần"
      - "Xét good nghiệp sớm"
      - "Quyết định về good nghiệp"
      - "Thông báo xét good nghiệp"
    embedding_model: "vietnamese-embedding-v2"
    similarity_threshold: 0.75

  - name: "hoc_ba"
    router: "RAGRouter"
    queries:
      - "Quy định học bạ"
      - "Điều kiện được miễn học bạ"
      - "Quy trình xét học bạ"
      - "Học bạ từng phần"
      - "Miễn giảm học bạ"
      - "Quy định về học bạ"
      - "Xét học bạ"
      - "Điều kiện xét học bạ"
      - "Quy trình xét học bạ"
      - "Học bạ đạt"
      - "Thời hạn học bạ"
    embedding_model: "vietnamese-embedding-v2"
    similarity_threshold: 0.75

  - name: "hoc_phi"
    router: "RAGRouter"
    queries:
      - "Mức học phí"
      - "Quy định học phí"
      - "Miễn giảm học phí"
      - "Thủ tục nộp học phí"
      - "Học phí các ngành"
      - "Biểu phí học phí"
      - "Học phí tín_only"
      - "Nộp học phí"
      - "Hạn mức học phí"
      - "Miễn giảm"
    embedding_model: "vietnamese-embedding-v2"
    similarity_threshold: 0.75

  - name: "quy_che"
    router: "RAGRouter"
    queries:
      - "Quy chế đào tạo"
      - "Quy chế sinh viên"
      - "Quy chế thi"
      - "Nội dung quy chế"
      - "Quy định chi tiết"
      - "Hướng dẫn thực hiện"
      - "Ban hành theo quy chế"
      - "Căn cứ quy chế"
      - "Theo quy chế"
      - "Quy định số"
    embedding_model: "vietnamese-embedding-v2"
    similarity_threshold: 0.75

  - name: "soan_van_ban"
    router: "RAGRouter"
    queries:
      - "Quyết định thành lập"
      - "Thành lập Hội đồng"
      "Ban hành văn bản"
      - "Phê duyệt quyết định"
      - "Ký ban hành"
      - "Dự thảo văn bản"
      - "Soạn thảo văn bản"
      - "Lập tờ trình"
    embedding_model: "vietnamese-embedding-v2"
    similarity_threshold: 0.70


__all__ = [
    "ROUTING_CLASSIFIER_PROMPT",
    "OPTION_1_NO_QUICK_FILTER",
    "OPTION_2_IMPROVED_LLM_CLASSIFIER",
    "OPTION_3_LOWERED_THRESHOLD",
    "SEMANTIC_ROUTES_CONFIG",
]
