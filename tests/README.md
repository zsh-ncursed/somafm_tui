# Testing Guide for SomaFM TUI Player

## Running Tests

### Basic Test Run
```bash
# Run all tests
pytest

# Or using Python module
python -m pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_config.py

# Run specific test class
pytest tests/test_config.py::TestValidateConfig

# Run specific test function
pytest tests/test_config.py::TestValidateConfig::test_valid_config_unchanged
```

### Test Coverage
```bash
# Run with coverage report
pytest --cov=somafm_tui --cov-report=term-missing

# Run with HTML coverage report
pytest --cov=somafm_tui --cov-report=html
# Open htmlcov/index.html in browser
```

### Test Selection
```bash
# Run tests matching keyword
pytest -k "config"

# Run tests by marker
pytest -m "not slow"

# Run only fast unit tests (exclude integration)
pytest -m "not integration"
```

### Test Options
```bash
# Show local variables on failure
pytest -l

# Stop on first failure
pytest -x

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Show slowest tests
pytest --durations=10
```

## Project Structure

```
tests/
├── __init__.py           # Test package marker
├── conftest.py           # Pytest fixtures and shared setup
├── test_bitrate_utils.py # Tests for bitrate utilities
├── test_cli.py           # Tests for CLI argument parsing
├── test_config.py        # Tests for configuration module
├── test_models.py        # Tests for data models
├── test_themes.py        # Tests for theme system
└── test_timer.py         # Tests for sleep timer
```

## Writing New Tests

### Test File Naming
- Name test files as `test_<module>.py`
- Place in `tests/` directory
- Import from `somafm_tui` package

### Test Class Structure
```python
"""Tests for <module> module."""

import pytest
from somafm_tui.<module> import <function>


class Test<Feature>:
    """Tests for <feature>."""

    def test_description(self):
        """Should do something."""
        # Arrange
        value = create_test_data()
        
        # Act
        result = function_under_test(value)
        
        # Assert
        assert result == expected_value
```

### Using Fixtures

Fixtures are defined in `conftest.py`:

```python
def test_uses_fixture(sample_channel_data):
    """Test that uses sample data fixture."""
    channel = Channel.from_api_response(sample_channel_data)
    assert channel.id == "dronezone"
```

Available fixtures:
- `sample_channel_data` - Sample SomaFM API response
- `sample_config_dict` - Sample configuration dictionary
- `sample_track_metadata` - Sample track metadata
- `mock_curses` - Mocked curses module
- `temp_config_file` - Temporary config file
- `mock_requests` - Mocked requests module

### Mocking External Dependencies

```python
from unittest.mock import patch

def test_with_mock():
    """Test with mocked dependency."""
    with patch('somafm_tui.module.function') as mock_func:
        mock_func.return_value = "mocked"
        result = call_function()
        assert result == "mocked"
```

### Testing CLI Output

```python
def test_print_output(capsys):
    """Test console output."""
    print_channels([channel])
    
    captured = capsys.readouterr()
    assert "Channel Name" in captured.out
```

## Test Categories

### Unit Tests (Default)
Fast, isolated tests with no external dependencies:
```bash
pytest -m "not integration"
```

### Integration Tests (Marked)
Tests that may use network or external services:
```python
@pytest.mark.integration
def test_api_call():
    ...
```

Run integration tests:
```bash
pytest -m integration
```

### Slow Tests (Marked)
Tests that take longer to run:
```python
@pytest.mark.slow
def test_large_dataset():
    ...
```

Exclude slow tests:
```bash
pytest -m "not slow"
```

## Configuration

Pytest configuration is in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
]
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Push to main branch

See `.github/workflows/tests.yml` for CI configuration.

## Coverage Goals

Current coverage targets:
- Core modules: 80%+
- Utility modules: 90%+
- Overall: 60-70%

Check coverage:
```bash
pytest --cov=somafm_tui --cov-report=term-missing
```

## Debugging Tests

### Show print statements
```bash
pytest -s
```

### Run single test with pdb
```bash
pytest --pdb tests/test_module.py::test_function
```

### Verbose output
```bash
pytest -vv
```

## Common Issues

### Import Errors
Make sure you're running from project root:
```bash
cd /path/to/somafm_tui
pytest
```

### Curses Errors
Tests mock curses module. If you see curses errors:
```python
def test_with_curses(mock_curses):
    """Test that needs curses mocked."""
    # mock_curses fixture handles this
```

### Test Isolation
Each test should be independent. Use fixtures for setup:
```python
def test_isolated(sample_config_dict):
    """Test doesn't depend on other tests."""
```
