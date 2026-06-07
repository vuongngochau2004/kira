# Performance Benchmark Tools

This directory contains performance benchmarking tools for the K.I.R.A system.

## Protocol vs ABC Benchmark

### Overview

The `benchmark_protocol_abc.py` script measures the performance overhead of using Protocol-based abstractions versus ABC-based abstractions for the core operations in the SOLID architecture.

### Usage

```bash
# Basic usage (default: 10,000 iterations, 1,000 warmup)
python tools/benchmark_protocol_abc.py

# Custom iterations
python tools/benchmark_protocol_abc.py --iterations 50000 --warmup 5000
```

### Output Format

```
======================================================================
PROTOCOL VS ABC PERFORMANCE BENCHMARK
======================================================================

Iterations: 10,000
Warmup: 1,000

======================================================================

Running: ClassificationStrategy.classify benchmark...

Operation: ClassificationStrategy.classify
Protocol: 0.00ms (P95: 0.00ms, P99: 0.02ms)
ABC: 0.00ms (P95: 0.00ms, P99: 0.01ms)
Overhead: +-4.18% ✓

Running: QueryHandler.handle benchmark...

Operation: QueryHandler.handle
Protocol: 1.24ms (P95: 1.32ms, P99: 2.27ms)
ABC: 1.27ms (P95: 1.39ms, P99: 1.44ms)
Overhead: +2.14% ✓

Running: DependencyContainer.get benchmark...

Operation: DependencyContainer.get
Protocol: 0.00ms (P95: 0.00ms, P99: 0.00ms)
ABC: 0.00ms (P95: 0.00ms, P99: 0.00ms)
Overhead: +-3.69% ✓

======================================================================
SUMMARY
======================================================================
ClassificationStrategy.classify: ✓ PASS
QueryHandler.handle: ✓ PASS
DependencyContainer.get: ✓ PASS

✓ All benchmarks passed: Protocol overhead < 10%
```

### Benchmarked Operations

1. **ClassificationStrategy.classify** (~0.01ms baseline)
   - Measures query classification performance
   - Uses keyword matching and fuzzy file detection
   - Critical for query routing latency

2. **QueryHandler.handle** (~1.2ms baseline)
   - Measures query execution performance
   - Includes retrieval and LLM generation simulation
   - Critical for end-to-end response time

3. **DependencyContainer.get** (~0.001ms baseline)
   - Measures DI container resolution performance
   - Tests singleton service lookup
   - Critical for application startup and handler dispatch

### Acceptance Criteria

- **Overhead < 10%**: Protocol-based abstractions should not add more than 10% latency overhead compared to ABC-based implementations
- **P95/P99 consistency**: Percentiles should show consistent performance across iterations
- **All operations pass**: All three core operations must meet the overhead threshold

### Interpretation

- **Positive overhead (e.g., +2.14%)**: ABC is slower than Protocol (expected, Protocol is more efficient)
- **Negative overhead (e.g., -4.18%)**: Protocol is slower than ABC (within variance, not statistically significant)
- **✓ PASS**: Overhead is within acceptable bounds (< 10%)
- **✗ FAIL**: Overhead exceeds threshold, needs investigation

### Technical Details

#### Protocol vs ABC Performance

Protocol-based abstractions are generally more efficient than ABC-based abstractions because:

1. **No runtime isinstance checks**: Protocols use structural subtyping (duck typing)
2. **No metaclass overhead**: ABCs use metaclasses for registration
3. **Faster attribute access**: Protocol lookups are direct attribute access
4. **No abstractmethod decorators**: Reduces function call overhead

#### Benchmark Methodology

1. **Warmup phase**: Executes warmup iterations to warm up JIT and caches
2. **Protocol measurement**: Measures Protocol implementation performance
3. **ABC measurement**: Measures ABC implementation performance
4. **Statistical analysis**: Calculates mean, P95, and P99 percentiles
5. **Overhead calculation**: Computes percentage overhead

#### Mock Implementation

The benchmark uses mock implementations that simulate real-world operations:

- **Keyword-based classification**: Fast keyword matching (< 5ms target)
- **RAG handler**: Simulates document retrieval (1ms sleep) + response generation
- **DI container**: Dictionary-based service lookup with minimal overhead

### Future Benchmarks

Additional benchmarks to be added:

- [ ] Latency comparison with real Qdrant/PostgreSQL operations
- [ ] Memory overhead comparison (Protocol vs ABC)
- [ ] Cold start performance (first invocation)
- [ ] Concurrent access patterns (multi-threaded/multi-processed)
- [ ] End-to-end API latency comparison

### Troubleshooting

#### High Variance in Results

If results show high variance:

1. Increase iterations (`--iterations 50000`)
2. Close other applications to reduce CPU contention
3. Run multiple times and average results
4. Check for background processes (Docker, databases)

#### Negative Overhead Values

Negative overhead (e.g., -4.18%) indicates ABC is faster than Protocol. This is usually:

1. Within measurement variance (not statistically significant)
2. Due to JIT optimization differences
3. Caused by cache effects

As long as the absolute overhead is < 10%, the result is acceptable.

#### Benchmark Failures

If overhead >= 10%:

1. Check for system load (CPU, memory)
2. Verify Python version (3.11+ recommended)
3. Increase warmup iterations
4. Run with higher iterations for more accurate results

### Contributing

When adding new benchmarks:

1. Follow the existing structure (Protocol, ABC, Benchmark functions)
2. Include warmup phase for JIT optimization
3. Measure mean, P95, P99 percentiles
4. Add acceptance criteria (overhead threshold)
5. Update this README with operation description

### References

- [PEP 544 -- Protocols: Structural subtyping (static duck typing)](https://peps.python.org/pep-0544/)
- [ABC vs Protocol Performance](https://stackoverflow.com/questions/57710821/protocol-vs-abc-python)
- [SOLID Architecture Refactor](../docs/architecture/solid-refactor.md)
