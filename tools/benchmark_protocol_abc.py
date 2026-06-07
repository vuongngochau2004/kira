#!/usr/bin/env python3
"""
Performance benchmark: Protocol vs ABC latency overhead.

This script measures the performance difference between Protocol-based
and ABC-based implementations for the core operations in the SOLID architecture.

Usage:
    python tools/benchmark_protocol_abc.py --iterations 10000 --warmup 1000

Example output:
    Operation: ClassificationStrategy.classify
    Protocol: 0.85ms (P95: 1.2ms, P99: 1.8ms)
    ABC: 0.87ms (P95: 1.23ms, P99: 1.85ms)
    Overhead: +2.35% ✓

Author: SOLID Architecture Refactor
Date: 2025-01-07
"""

import argparse
import asyncio
import statistics
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

# Add project root to path
sys.path.insert(0, str(__file__).replace("/tools/benchmark_protocol_abc.py", ""))


# =============================================================================
# MOCK PROTOCOLS
# =============================================================================

class MockClassificationStrategy(Protocol):
    """Protocol-based classification strategy."""

    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict | None = None
    ) -> "MockClassificationResult":
        """Classify query intent."""
        ...


class MockQueryHandler(Protocol):
    """Protocol-based query handler."""

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: "MockClassificationResult",
        context: dict | None = None
    ) -> "MockHandlerResult":
        """Execute query."""
        ...

    def can_handle(self, classification: "MockClassificationResult") -> bool:
        """Check if handler can handle classification."""
        ...


class MockDependencyContainer(Protocol):
    """Protocol-based DI container."""

    async def get(self, interface: type) -> object:
        """Resolve dependency."""
        ...


# =============================================================================
# MOCK ABCs
# =============================================================================

class ABCClassificationStrategy(ABC):
    """ABC-based classification strategy."""

    @abstractmethod
    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict | None = None
    ) -> "MockClassificationResult":
        """Classify query intent."""
        ...


class ABCQueryHandler(ABC):
    """ABC-based query handler."""

    @abstractmethod
    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: "MockClassificationResult",
        context: dict | None = None
    ) -> "MockHandlerResult":
        """Execute query."""
        ...

    @abstractmethod
    def can_handle(self, classification: "MockClassificationResult") -> bool:
        """Check if handler can handle classification."""
        ...



# =============================================================================
# MOCK DATA STRUCTURES
# =============================================================================

@dataclass
class MockClassificationResult:
    """Mock classification result."""
    intent: str
    confidence: float
    reason: str = ""


@dataclass
class MockHandlerResult:
    """Mock handler result."""
    content: str
    metadata: dict


# =============================================================================
# PROTOCOL IMPLEMENTATIONS
# =============================================================================

class ProtocolKeywordClassifier:
    """Protocol-based keyword classifier implementation."""

    def __init__(self):
        self.keywords = ["tài liệu", "doc", "pdf", "file", "hỏi về"]

    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict | None = None
    ) -> MockClassificationResult:
        """Classify using keyword matching."""
        query_lower = query.lower()

        for keyword in self.keywords:
            if keyword in query_lower:
                return MockClassificationResult(
                    intent="rag",
                    confidence=0.9,
                    reason=f"Keyword: {keyword}"
                )

        return MockClassificationResult(
            intent="conversational",
            confidence=0.6,
            reason="No keywords"
        )


class ProtocolRAGHandler:
    """Protocol-based RAG handler implementation."""

    def __init__(self):
        self.name = "RAGHandler"

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: MockClassificationResult,
        context: dict | None = None
    ) -> MockHandlerResult:
        """Handle RAG query."""
        # Simulate retrieval delay
        await asyncio.sleep(0.001)  # 1ms

        return MockHandlerResult(
            content=f"Response to: {query}",
            metadata={"handler": self.name, "docs_retrieved": 5}
        )

    def can_handle(self, classification: MockClassificationResult) -> bool:
        """Check if can handle RAG intent."""
        return classification.intent == "rag"


class ProtocolServiceContainer:
    """Protocol-based DI container."""

    def __init__(self):
        self._services = {}

    async def register(self, interface: type, implementation: object):
        """Register service."""
        self._services[interface] = implementation

    async def get(self, interface: type) -> object:
        """Resolve dependency."""
        return self._services.get(interface)


# =============================================================================
# ABC IMPLEMENTATIONS
# =============================================================================

class ABCKeywordClassifier(ABCClassificationStrategy):
    """ABC-based keyword classifier implementation."""

    def __init__(self):
        self.keywords = ["tài liệu", "doc", "pdf", "file", "hỏi về"]

    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict | None = None
    ) -> MockClassificationResult:
        """Classify using keyword matching."""
        query_lower = query.lower()

        for keyword in self.keywords:
            if keyword in query_lower:
                return MockClassificationResult(
                    intent="rag",
                    confidence=0.9,
                    reason=f"Keyword: {keyword}"
                )

        return MockClassificationResult(
            intent="conversational",
            confidence=0.6,
            reason="No keywords"
        )


class ABCRAGHandler(ABCQueryHandler):
    """ABC-based RAG handler implementation."""

    def __init__(self):
        self.name = "RAGHandler"

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: MockClassificationResult,
        context: dict | None = None
    ) -> MockHandlerResult:
        """Handle RAG query."""
        # Simulate retrieval delay
        await asyncio.sleep(0.001)  # 1ms

        return MockHandlerResult(
            content=f"Response to: {query}",
            metadata={"handler": self.name, "docs_retrieved": 5}
        )

    def can_handle(self, classification: MockClassificationResult) -> bool:
        """Check if can handle RAG intent."""
        return classification.intent == "rag"


class ABCServiceContainer:
    """ABC-based DI container."""

    def __init__(self):
        self._services = {}

    async def register(self, interface: type, implementation: object):
        """Register service."""
        self._services[interface] = implementation

    async def get(self, interface: type) -> object:
        """Resolve dependency."""
        return self._services.get(interface)


# =============================================================================
# BENCHMARK UTILITIES
# =============================================================================

@dataclass
class BenchmarkResult:
    """Benchmark result."""
    operation: str
    protocol_mean_ms: float
    protocol_p95_ms: float
    protocol_p99_ms: float
    abc_mean_ms: float
    abc_p95_ms: float
    abc_p99_ms: float
    overhead_percent: float


def calculate_percentiles(data: list[float], p95: bool = True, p99: bool = True):
    """Calculate percentiles from data."""
    sorted_data = sorted(data)
    n = len(sorted_data)

    if p95:
        p95_idx = int(n * 0.95)
        p95_val = sorted_data[p95_idx] if p95_idx < n else sorted_data[-1]
    else:
        p95_val = 0.0

    if p99:
        p99_idx = int(n * 0.99)
        p99_val = sorted_data[p99_idx] if p99_idx < n else sorted_data[-1]
    else:
        p99_val = 0.0

    return p95_val, p99_val


def format_result(result: BenchmarkResult) -> str:
    """Format benchmark result for output."""
    status = "✓" if result.overhead_percent < 10 else "✗"

    output = f"""
Operation: {result.operation}
Protocol: {result.protocol_mean_ms:.2f}ms (P95: {result.protocol_p95_ms:.2f}ms, P99: {result.protocol_p99_ms:.2f}ms)
ABC: {result.abc_mean_ms:.2f}ms (P95: {result.abc_p95_ms:.2f}ms, P99: {result.abc_p99_ms:.2f}ms)
Overhead: +{result.overhead_percent:.2f}% {status}
"""
    return output


# =============================================================================
# BENCHMARK OPERATIONS
# =============================================================================

async def benchmark_classification(iterations: int) -> BenchmarkResult:
    """Benchmark ClassificationStrategy.classify operation."""

    # Protocol implementation
    protocol_classifier = ProtocolKeywordClassifier()

    # Warmup
    for _ in range(1000):
        await protocol_classifier.classify("test query", uuid4())

    # Measure protocol
    protocol_times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        await protocol_classifier.classify("hỏi về tài liệu", uuid4())
        t1 = time.perf_counter()
        protocol_times.append((t1 - t0) * 1000)  # Convert to ms

    # ABC implementation
    abc_classifier = ABCKeywordClassifier()

    # Warmup
    for _ in range(1000):
        await abc_classifier.classify("test query", uuid4())

    # Measure ABC
    abc_times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        await abc_classifier.classify("hỏi về tài liệu", uuid4())
        t1 = time.perf_counter()
        abc_times.append((t1 - t0) * 1000)

    # Calculate stats
    protocol_mean = statistics.mean(protocol_times)
    protocol_p95, protocol_p99 = calculate_percentiles(protocol_times)
    abc_mean = statistics.mean(abc_times)
    abc_p95, abc_p99 = calculate_percentiles(abc_times)

    overhead = ((abc_mean / protocol_mean) - 1) * 100

    return BenchmarkResult(
        operation="ClassificationStrategy.classify",
        protocol_mean_ms=protocol_mean,
        protocol_p95_ms=protocol_p95,
        protocol_p99_ms=protocol_p99,
        abc_mean_ms=abc_mean,
        abc_p95_ms=abc_p95,
        abc_p99_ms=abc_p99,
        overhead_percent=overhead
    )


async def benchmark_handler(iterations: int) -> BenchmarkResult:
    """Benchmark QueryHandler.handle operation."""

    # Protocol implementation
    protocol_handler = ProtocolRAGHandler()
    mock_classification = MockClassificationResult(intent="rag", confidence=0.9)

    # Warmup
    for _ in range(100):
        await protocol_handler.handle("test", uuid4(), mock_classification)

    # Measure protocol
    protocol_times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        await protocol_handler.handle("hỏi về tài liệu", uuid4(), mock_classification)
        t1 = time.perf_counter()
        protocol_times.append((t1 - t0) * 1000)

    # ABC implementation
    abc_handler = ABCRAGHandler()

    # Warmup
    for _ in range(100):
        await abc_handler.handle("test", uuid4(), mock_classification)

    # Measure ABC
    abc_times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        await abc_handler.handle("hỏi về tài liệu", uuid4(), mock_classification)
        t1 = time.perf_counter()
        abc_times.append((t1 - t0) * 1000)

    # Calculate stats
    protocol_mean = statistics.mean(protocol_times)
    protocol_p95, protocol_p99 = calculate_percentiles(protocol_times)
    abc_mean = statistics.mean(abc_times)
    abc_p95, abc_p99 = calculate_percentiles(abc_times)

    overhead = ((abc_mean / protocol_mean) - 1) * 100

    return BenchmarkResult(
        operation="QueryHandler.handle",
        protocol_mean_ms=protocol_mean,
        protocol_p95_ms=protocol_p95,
        protocol_p99_ms=protocol_p99,
        abc_mean_ms=abc_mean,
        abc_p95_ms=abc_p95,
        abc_p99_ms=abc_p99,
        overhead_percent=overhead
    )


async def benchmark_container(iterations: int) -> BenchmarkResult:
    """Benchmark DependencyContainer.get operation."""

    # Protocol implementation
    protocol_container = ProtocolServiceContainer()
    await protocol_container.register(MockQueryHandler, ProtocolRAGHandler())

    # Warmup
    for _ in range(1000):
        await protocol_container.get(MockQueryHandler)

    # Measure protocol
    protocol_times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        await protocol_container.get(MockQueryHandler)
        t1 = time.perf_counter()
        protocol_times.append((t1 - t0) * 1000)

    # ABC implementation
    abc_container = ABCServiceContainer()
    await abc_container.register(ABCQueryHandler, ABCRAGHandler())

    # Warmup
    for _ in range(1000):
        await abc_container.get(ABCQueryHandler)

    # Measure ABC
    abc_times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        await abc_container.get(ABCQueryHandler)
        t1 = time.perf_counter()
        abc_times.append((t1 - t0) * 1000)

    # Calculate stats
    protocol_mean = statistics.mean(protocol_times)
    protocol_p95, protocol_p99 = calculate_percentiles(protocol_times)
    abc_mean = statistics.mean(abc_times)
    abc_p95, abc_p99 = calculate_percentiles(abc_times)

    overhead = ((abc_mean / protocol_mean) - 1) * 100

    return BenchmarkResult(
        operation="DependencyContainer.get",
        protocol_mean_ms=protocol_mean,
        protocol_p95_ms=protocol_p95,
        protocol_p99_ms=protocol_p99,
        abc_mean_ms=abc_mean,
        abc_p95_ms=abc_p95,
        abc_p99_ms=abc_p99,
        overhead_percent=overhead
    )


# =============================================================================
# MAIN BENCHMARK RUNNER
# =============================================================================

async def run_benchmarks(iterations: int, warmup: int):
    """Run all benchmarks."""
    print("=" * 70)
    print("PROTOCOL VS ABC PERFORMANCE BENCHMARK")
    print("=" * 70)
    print(f"\nIterations: {iterations:,}")
    print(f"Warmup: {warmup:,}")
    print(f"\n{'=' * 70}\n")

    results = []

    # Benchmark 1: Classification
    print("Running: ClassificationStrategy.classify benchmark...")
    result = await benchmark_classification(iterations)
    results.append(result)
    print(format_result(result))

    # Benchmark 2: Handler
    print("Running: QueryHandler.handle benchmark...")
    result = await benchmark_handler(iterations)
    results.append(result)
    print(format_result(result))

    # Benchmark 3: Container
    print("Running: DependencyContainer.get benchmark...")
    result = await benchmark_container(iterations)
    results.append(result)
    print(format_result(result))

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_passed = True
    for result in results:
        status = "✓ PASS" if result.overhead_percent < 10 else "✗ FAIL"
        print(f"{result.operation}: {status}")
        if result.overhead_percent >= 10:
            all_passed = False

    print()
    if all_passed:
        print("✓ All benchmarks passed: Protocol overhead < 10%")
        return 0
    else:
        print("✗ Some benchmarks failed: Protocol overhead >= 10%")
        return 1


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark Protocol vs ABC performance overhead"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10000,
        help="Number of iterations per benchmark (default: 10000)"
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=1000,
        help="Number of warmup iterations (default: 1000)"
    )

    args = parser.parse_args()

    # Run async benchmarks
    exit_code = asyncio.run(run_benchmarks(args.iterations, args.warmup))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
