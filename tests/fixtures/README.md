# ABC Fixtures - Protocol to ABC Migration Testing

ABC-compatible test fixtures for testing Protocol-based interfaces alongside their ABC equivalents during migration.

## 🎯 Purpose

Support testing during Protocol → ABC migration by providing:
- ABC mock implementations for all core protocols
- Protocol vs ABC comparison utilities
- Performance benchmarking tools
- Compliance validation helpers

## 📦 Components

### ABC Classes
- `ClassificationStrategyABC` - ABC version of ClassificationStrategy
- `QueryHandlerABC` - ABC version of QueryHandler  
- `DependencyContainerABC` - ABC version of DependencyContainer

### Mock Implementations
- `MockClassificationStrategyABC` - Mock classification with configurable intent/confidence
- `MockQueryHandlerABC` - Mock handler with citations support
- `MockDependencyContainerABC` - Mock DI container with singleton resolution

### Protocol Counterparts
- `MockClassificationStrategyProtocol` - Protocol version for comparison
- `MockQueryHandlerProtocol` - Protocol handler for comparison

## 🚀 Pytest Fixtures

### `abc_implementation`
Create mock ABC implementation dynamically:

```python
def test_abc_usage(abc_implementation):
    impl = abc_implementation(ClassificationStrategyABC)
    result = await impl.classify("test query", "user123")
    assert result.intent == Intent.RAG
```

### `protocol_vs_abc`
Compare Protocol and ABC side-by-side:

```python
def test_consistency(protocol_vs_abc):
    protocol_impl, abc_impl = protocol_vs_abc(
        MockClassificationStrategyProtocol,
        ClassificationStrategyABC
    )
    result_p = await protocol_impl.classify("test", "user123")
    result_a = await abc_impl.classify("test", "user123")
    assert result_p.intent == result_a.intent
```

### `mock_classification_strategy`
Configurable mock classification strategy:

```python
def test_custom_config(mock_classification_strategy):
    strategy = mock_classification_strategy(
        intent=Intent.CONVERSATIONAL,
        confidence=0.85
    )
    result = await strategy.classify("hello", "user123")
    assert result.intent == Intent.CONVERSATIONAL
```

### `mock_query_handler`
Configurable mock query handler with citations:

```python
def test_handler_with_citations(mock_query_handler):
    handler = mock_query_handler(
        content="Response",
        citations=[Citation(filename="doc.pdf", page=1, text="...")]
    )
    result = await handler.handle("query", "user123", classification)
    assert len(result.citations) == 1
```

### `mock_dependency_container`
Mock DI container for testing:

```python
async def test_container(mock_dependency_container):
    container = mock_dependency_container()
    await container.register_singleton(
        ClassificationStrategyABC,
        MockClassificationStrategyABC()
    )
    strategy = await container.get(ClassificationStrategyABC)
    assert strategy is not None
```

### `sample_classification_result`
Sample classification result for testing.

### `sample_citations`
Sample citations (2 items) for testing.

### `sample_handler_config`
Sample HandlerConfig for testing.

### `initialized_di_container`
Fully initialized container with pre-registered services.

### `abc_migration_suite`
Complete suite with all components for migration testing.

## 🛠️ Helper Functions

### `create_abc_mock(abc_class)`
Generate mock implementation for ABC class:

```python
impl = create_abc_mock(ClassificationStrategyABC)
result = await impl.classify("test", "user123")
```

### `assert_abc_compliance(abc_class, implementation)`
Verify implementation satisfies ABC abstract methods:

```python
assert_abc_compliance(ClassificationStrategyABC, MockClassificationStrategyABC)
```

### `benchmark_abc_vs_protocol(protocol_class, abc_class, iterations)`
Performance comparison between Protocol and ABC:

```python
results = await benchmark_abc_vs_protocol(
    MockClassificationStrategyProtocol,
    ClassificationStrategyABC,
    iterations=1000
)
print(f"Protocol: {results['protocol_time']:.4f}s")
print(f"ABC: {results['abc_time']:.4f}s")
print(f"Speedup: {results['speedup_ratio']:.2f}x")
```

### `measure_protocol_overhead(protocol_impl, method, *args, **kwargs)`
Measure protocol execution overhead:

```python
overhead = measure_protocol_overhead(strategy, "classify", "test", "user123")
print(f"Execution time: {overhead['execution_time_ms']:.2f}ms")
```

### `verify_protocol_compatibility(protocol, impl)`
Verify structural compatibility with Protocol:

```python
is_compatible = verify_protocol_compatibility(ClassificationStrategy, impl)
assert is_compatible
```

## 📋 Test Categories

### Basic Tests
- ABC implementation creation
- Mock instantiation
- Fixture availability

### Compliance Tests
- Abstract method implementation verification
- Signature validation
- Type checking

### Async Execution Tests
- Async method execution
- Container service resolution
- Singleton behavior

### Comparison Tests
- Protocol vs ABC consistency
- Behavior equivalence
- Result validation

### Performance Tests
- Benchmarking Protocol vs ABC
- Overhead measurement
- Speedup ratio calculation

### Integration Tests
- Full pipeline testing
- Container with multiple services
- End-to-end workflows

### Edge Cases
- Empty query handling
- Low confidence classifications
- Unregistered service errors
- Non-compliant implementations

## 🧪 Example Test Suite

See `test_abc_fixtures_examples.py` for comprehensive examples:

```bash
# Run all ABC fixture tests
pytest tests/fixtures/test_abc_fixtures_examples.py -v

# Run specific test category
pytest tests/fixtures/test_abc_fixtures_examples.py::TestABCCompliance -v

# Run with coverage
pytest tests/fixtures/test_abc_fixtures_examples.py --cov=tests.fixtures
```

## 🔧 Migration Testing Workflow

1. **Create ABC Equivalent**
   ```python
   class MyProtocolABC(ABC):
       @abstractmethod
       async def my_method(self, arg: str) -> Result:
           pass
   ```

2. **Implement Mock**
   ```python
   class MyMockABC(MyProtocolABC):
       async def my_method(self, arg: str) -> Result:
           return Result(...)
   ```

3. **Add to Fixtures**
   ```python
   # In abc_fixtures.py
   @pytest.fixture
   def mock_my_implementation():
       return MyMockABC()
   ```

4. **Test Compliance**
   ```python
   def test_compliance():
       assert_abc_compliance(MyProtocolABC, MyMockABC)
   ```

5. **Compare with Protocol**
   ```python
   @pytest.mark.asyncio
   async def test_protocol_vs_abc():
       results = await benchmark_abc_vs_protocol(
           ProtocolImpl,
           MyProtocolABC
       )
       assert results["speedup_ratio"] > 0.9  # Within 10%
   ```

## 📊 Test Results

Current suite: **31 tests passing**

- ✅ Basic ABC implementation (3 tests)
- ✅ ABC compliance validation (3 tests)
- ✅ Fixture-based tests (5 tests)
- ✅ Async execution (4 tests)
- ✅ Protocol vs ABC comparison (2 tests)
- ✅ Performance benchmarking (2 tests)
- ✅ Integration tests (3 tests)
- ✅ Edge cases (4 tests)
- ✅ Test data fixtures (3 tests)
- ✅ Protocol compatibility (2 tests)

## 🎓 Best Practices

1. **Use Fixtures Over Direct Creation**: Fixtures provide consistent setup/teardown
2. **Test Both Protocol and ABC**: Ensure migration maintains behavior
3. **Benchmark Performance**: Verify no significant regression
4. **Validate Compliance**: Catch missing implementations early
5. **Test Edge Cases**: Empty inputs, low confidence, errors

## 📝 File Structure

```
tests/fixtures/
├── __init__.py                    # Fixture exports
├── conftest.py                     # Pytest configuration
├── abc_fixtures.py                 # Main fixtures file
├── test_abc_fixtures_examples.py  # Example tests
└── README.md                       # This file
```

## 🔗 Related Documentation

- [Protocol Documentation](/src/protocols/README.md)
- [ABC Migration Guide](/docs/abc-migration-guide.md)
- [Testing Best Practices](/docs/testing-guide.md)

## 🤝 Contributing

When adding new fixtures:

1. Create ABC class if needed
2. Implement mock with realistic behavior
3. Add pytest fixture
4. Write example tests
5. Update this README

## 📄 License

Part of K.I.R.A Simplified project.
