#!/usr/bin/env python3
"""Test chat routing functionality with semantic router."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def test_semantic_router():
    """Test semantic router directly."""
    print("=" * 60)
    print("🔧 TEST 1: Semantic Router Direct Test")
    print("=" * 60)

    from src.agents.routers.semantic import KIRASemanticRouter

    print("\nInitializing Semantic Router...")
    router = KIRASemanticRouter(threshold=0.75)

    test_cases = [
        ("xin chào", "ConversationalRouter"),
        ("bạn tên gì", "ConversationalRouter"),
        ("cảm ơn", "ConversationalRouter"),
        ("hợp đồng", "RAGRouter"),
        ("luật", "RAGRouter"),
        ("nghị định", "RAGRouter"),
        ("quy định", "RAGRouter"),
        ("điều khoản hợp đồng", "RAGRouter"),
    ]

    print("\n📊 Routing Results:\n")
    passed = 0
    failed = 0

    for query, expected in test_cases:
        result = router.route(query)
        if result and result["router_name"] == expected:
            print(f"✅ '{query}' → {result['router_name']} (score: {result['score']:.2f})")
            passed += 1
        else:
            status = "below threshold" if not result else f"got {result['router_name']}"
            print(f"❌ '{query}' → Expected {expected}, {status}")
            failed += 1

    print(f"\n📈 Result: {passed}/{len(test_cases)} passed")
    return failed == 0


async def test_orchestrator_routing():
    """Test orchestrator routing with semantic router."""
    print("\n" + "=" * 60)
    print("🔧 TEST 2: Orchestrator Integration Test")
    print("=" * 60)

    from src.agents.orchestrator import create_orchestrator

    print("\nInitializing Orchestrator with semantic router...")
    orchestrator = create_orchestrator(enable_semantic=True)

    test_queries = [
        ("xin chào", "conversational"),
        ("hợp đồng", "rag_legal"),  # Critical test
        ("quy định lao động", "rag_legal"),
    ]

    print("\n📊 Orchestrator Routing Results:\n")

    for query, expected_semantic_route in test_queries:
        result = await orchestrator.query(query, user_id="test")
        metadata = result.get("metadata", {})
        routing_method = metadata.get("routing_method")
        semantic_route = metadata.get("semantic_route")

        print(f"\nQuery: '{query}'")
        print(f"  Routing Method: {routing_method}")

        if routing_method == "semantic":
            if semantic_route == expected_semantic_route:
                print(f"  ✅ Semantic route: {semantic_route} (correct)")
            else:
                print(f"  ❌ Semantic route: {semantic_route} (expected {expected_semantic_route})")
        else:
            print(f"  ⚠️  Not using semantic routing (using {routing_method})")

    return True


async def test_edge_cases():
    """Test edge cases."""
    print("\n" + "=" * 60)
    print("🔧 TEST 3: Edge Cases Test")
    print("=" * 60)

    from src.agents.routers.semantic import KIRASemanticRouter

    router = KIRASemanticRouter(threshold=0.75)

    edge_cases = [
        ("", "Empty query"),
        ("xyz123", "Unknown query"),
        ("a", "Single character"),
        ("hợp đồng lao động theo pháp luật việt nam", "Long query with keywords"),
    ]

    print("\n📊 Edge Case Results:\n")

    for query, description in edge_cases:
        result = router.route(query)
        if result:
            print(f"✅ '{description}' → {result['router_name']} (score: {result['score']:.2f})")
        else:
            print(f"⚠️  '{description}' → Below threshold (returns None)")

    return True


async def main():
    """Run all tests."""
    print("\n" + "🚀" * 30)
    print("KIRA Chat Routing Test Suite")
    print("Testing Semantic Router Implementation")
    print("🚀" * 30 + "\n")

    results = []

    # Test 1: Direct semantic router
    try:
        result = await test_semantic_router()
        results.append(("Semantic Router Direct", result))
    except Exception as e:
        print(f"❌ Test 1 failed with error: {e}")
        results.append(("Semantic Router Direct", False))

    # Test 2: Orchestrator integration
    try:
        result = await test_orchestrator_routing()
        results.append(("Orchestrator Integration", True))
    except Exception as e:
        print(f"❌ Test 2 failed with error: {e}")
        results.append(("Orchestrator Integration", False))

    # Test 3: Edge cases
    try:
        result = await test_edge_cases()
        results.append(("Edge Cases", True))
    except Exception as e:
        print(f"❌ Test 3 failed with error: {e}")
        results.append(("Edge Cases", False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
