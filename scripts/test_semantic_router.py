#!/usr/bin/env python3
"""Quick validation script for semantic router accuracy."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def test_semantic_router():
    """Test semantic router with sample queries."""
    from src.agents.routers.semantic import KIRASemanticRouter

    print("🔧 Initializing Semantic Router...")
    router = KIRASemanticRouter(threshold=0.75)

    print("\n📊 Test Queries:\n")

    test_cases = [
        # Conversational queries
        ("xin chào", "ConversationalRouter"),
        ("bạn tên gì", "ConversationalRouter"),
        ("cảm ơn", "ConversationalRouter"),
        ("tạm biệt", "ConversationalRouter"),

        # RAG queries (short - critical fix!)
        ("hợp đồng", "RAGRouter"),
        ("luật", "RAGRouter"),
        ("nghị định", "RAGRouter"),
        ("quy định", "RAGRouter"),

        # RAG queries (long)
        ("điều khoản hợp đồng lao động", "RAGRouter"),
        ("quy định về thời giờ làm việc", "RAGRouter"),
        ("thủ tục thành lập doanh nghiệp", "RAGRouter"),
    ]

    passed = 0
    failed = 0

    for query, expected_router in test_cases:
        result = router.route(query)

        if result is None:
            status = "❌ FAILED (below threshold)"
            failed += 1
        elif result["router_name"] == expected_router:
            status = f"✅ PASSED (score: {result['score']:.2f})"
            passed += 1
        else:
            status = f"❌ FAILED (got {result['router_name']})"
            failed += 1

        print(f"Query: '{query}'")
        print(f"Expected: {expected_router}")
        print(f"Status: {status}\n")

    # Summary
    total = passed + failed
    accuracy = (passed / total * 100) if total > 0 else 0

    print("=" * 50)
    print(f"📈 Results: {passed}/{total} passed ({accuracy:.1f}% accuracy)")
    print("=" * 50)

    if failed > 0:
        print(f"\n⚠️  {failed} queries failed")
        return 1
    else:
        print("\n✅ All queries passed!")
        return 0


async def test_integration():
    """Test full integration with RouterRegistry."""
    from src.agents.orchestrator import create_orchestrator

    print("\n🔧 Testing Integration with Orchestrator...")

    orchestrator = create_orchestrator(enable_semantic=True)

    test_queries = [
        ("xin chào", "conversational"),
        ("hợp đồng", "rag_legal"),  # Critical test
    ]

    print("\n📊 Integration Tests:\n")

    for query, expected_semantic_route in test_queries:
        result = await orchestrator.query(query, user_id="test")
        metadata = result.get("metadata", {})
        routing_method = metadata.get("routing_method")
        semantic_route = metadata.get("semantic_route")

        if routing_method == "semantic":
            if semantic_route == expected_semantic_route:
                print(f"✅ '{query}' → {semantic_route} (correct)")
            else:
                print(f"❌ '{query}' → {semantic_route} (expected {expected_semantic_route})")
        else:
            print(f"⚠️  '{query}' → {routing_method} (semantic not used)")

    return 0


async def main():
    """Run all tests."""
    print("=" * 50)
    print("KIRA Semantic Router Validation")
    print("=" * 50)

    exit_code = await test_semantic_router()

    if exit_code == 0:
        exit_code = await test_integration()

    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
