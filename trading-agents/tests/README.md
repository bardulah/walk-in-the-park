# Test Suite for Trading Agents System

This directory contains the test suite for the trading agents system.

## Running Tests

### Run all tests
```bash
cd trading-agents
pytest
```

### Run specific test file
```bash
pytest tests/test_base_agent.py
```

### Run with coverage
```bash
pytest --cov=agents --cov=config --cov=utils --cov-report=html
```

### Run only unit tests
```bash
pytest -m unit
```

### Run tests verbosely
```bash
pytest -v
```

## Test Structure

```
tests/
├── __init__.py                 # Test package
├── conftest.py                 # Shared fixtures and configuration
├── test_base_agent.py          # Tests for BaseAgent class
├── test_json_parser.py         # Tests for JSON parsing utilities
├── test_logging_config.py      # Tests for logging configuration
└── README.md                   # This file
```

## Test Fixtures

Common fixtures are defined in `conftest.py`:

- `mock_llm_router` - Mock LLM router for testing
- `sample_portfolio_data` - Sample portfolio data
- `sample_market_data` - Sample market data
- `sample_news_data` - Sample news data
- `valid_json_response` - Valid JSON response example
- `malformed_json_response` - Malformed JSON for robustness testing
- `markdown_wrapped_json` - JSON wrapped in markdown

## Writing New Tests

### Test Organization

Follow these patterns:

```python
class TestFeatureName:
    """Test specific feature"""

    def test_specific_behavior(self, fixture_name):
        """Test description"""
        # Arrange
        setup_data = {"key": "value"}

        # Act
        result = function_under_test(setup_data)

        # Assert
        assert result == expected_value
```

### Using Fixtures

```python
def test_with_mock_router(self, mock_llm_router):
    """Test using mock LLM router"""
    agent = MyAgent(mock_llm_router)
    # Test agent behavior
```

### Mocking

```python
from unittest.mock import Mock, patch

def test_with_mock():
    mock_obj = Mock()
    mock_obj.method.return_value = "mocked"
    assert mock_obj.method() == "mocked"
```

## Test Coverage

Current coverage areas:

- ✅ BaseAgent class - Full coverage
- ✅ JSON parser utilities - Full coverage
- ✅ Logging configuration - Full coverage
- ⏳ Individual agents - Pending
- ⏳ LLM routers - Pending
- ⏳ Risk manager - Pending
- ⏳ Orchestrator - Pending

## Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_example():
    """Unit test"""
    pass

@pytest.mark.integration
def test_integration_example():
    """Integration test"""
    pass

@pytest.mark.slow
def test_slow_example():
    """Slow test"""
    pass

@pytest.mark.requires_api
def test_api_example():
    """Test requiring API keys"""
    pass
```

Run specific markers:
```bash
pytest -m unit          # Run only unit tests
pytest -m "not slow"    # Skip slow tests
```

## Continuous Integration

Tests should pass in CI before merging:

```yaml
# Example CI configuration
- name: Run tests
  run: |
    cd trading-agents
    pytest --cov --cov-report=xml
```

## Best Practices

1. **Isolation** - Each test should be independent
2. **Clear Names** - Test names should describe what they test
3. **One Assertion Per Test** - Ideally, test one thing at a time
4. **Use Fixtures** - Reuse common setup code
5. **Mock External Dependencies** - Don't call real APIs in tests
6. **Fast Tests** - Keep tests fast (< 1s each if possible)
7. **Readable** - Tests serve as documentation

## Debugging Tests

### Run with print statements
```bash
pytest -s tests/test_file.py
```

### Run with debugger
```bash
pytest --pdb tests/test_file.py
```

### Run last failed tests only
```bash
pytest --lf
```

### Show local variables on failure
```bash
pytest -l
```

## Dependencies

Required packages for testing:
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting (optional)
- `pytest-mock` - Mocking utilities (optional)

Install with:
```bash
pip install pytest pytest-cov pytest-mock
```
