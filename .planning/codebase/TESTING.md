# Testing Patterns

**Analysis Date:** 2026-04-05

## Test Framework

**Runner:**
- pytest 7.0+ with strict markers
- Configured in `pyproject.toml` with:
  ```toml
  [tool.pytest.ini_options]
  minversion = "6.0"
  addopts = "-ra -q --strict-markers --cov=mobile_crawler --cov-report=html --cov-report=term-missing"
  testpaths = ["tests"]
  pythonpath = ["src"]
  markers = [
      "unit: marks tests as unit tests",
      "integration: marks tests as integration tests",
      "slow: marks tests as slow (deselect with '-m \"not slow\"')",
  ]
  ```

**Assertion Library:**
- Standard Python `assert` statements
- No custom assertion libraries

**Run Commands:**
```bash
pytest                           # Run all tests
pytest -m unit                   # Run unit tests only
pytest -m integration            # Run integration tests only
pytest -m "not slow"            # Skip slow tests
pytest --cov=mobile_crawler     # Run with coverage
pytest --cov-report=html        # Generate HTML coverage report
```

## Test File Organization

**Location:**
- Co-located with source code: `tests/` mirrors `src/` structure
- Example: `src/mobile_crawler/cli/main.py` → `tests/cli/test_main.py`

**Naming:**
- Test files: `test_<module>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<scenario>`

**Structure:**
```
tests/
├── cli/
│   ├── test_config_command.py
│   ├── test_crawl_command.py
│   └── ...
├── config/
│   ├── test_config_manager.py
│   └── ...
├── core/
│   ├── test_crawl_controller.py
│   ├── test_logging.py
│   └── ...
└── conftest.py                  # Shared fixtures
```

## Test Structure

**Suite Organization:**
```python
class TestCrawlController:
    """Tests for CrawlController."""

    def test_init(self):
        """Test initialization."""
        controller = CrawlController()

        assert controller.state == CrawlControlState.STOPPED
        assert controller.is_stopped()
        assert not controller.is_running()
        assert not controller.is_paused()

    def test_pause_from_running(self):
        """Test pausing from running state."""
        controller = CrawlController()

        # Start running (simulate)
        controller._state = CrawlControlState.RUNNING

        # Pause
        controller.pause()

        assert controller.state == CrawlControlState.PAUSED
        assert controller.is_paused()
        assert not controller.is_running()
```

**Patterns:**
- Setup in `test_` method or with fixtures
- Clear test names describe scenario
- Assertion chains show expected behavior
- Mock external dependencies
- Testing edge cases and error conditions

## Mocking

**Framework:**
- `unittest.mock` from standard library
- `Mock`, `patch` decorators commonly used
- No additional mocking frameworks

**Patterns:**
```python
from unittest.mock import Mock, patch

@patch('mobile_crawler.config.config_manager.ConfigManager')
@patch('mobile_crawler.config.paths.get_app_data_dir')
def test_config_set_regular_value(self, mock_get_app_data_dir, mock_config_manager_cls):
    """Test setting a regular configuration value."""
    mock_config_manager = Mock()
    mock_config_manager_cls.return_value = mock_config_manager
    mock_get_app_data_dir.return_value = Mock()

    runner = CliRunner()
    result = runner.invoke(cli, ['config', 'set', 'max_steps', '100'])

    assert result.exit_code == 0
    assert 'Set config: max_steps = 100' in result.output
    mock_config_manager.set.assert_called_once_with('max_steps', 100)
```

**What to Mock:**
- External dependencies (database, API calls)
- File system operations
- Time-sensitive operations
- GUI components when testing CLI
- Network requests

**What NOT to Mock:**
- Business logic within the test
- Simple utility functions
- Data structures and algorithms
- Core Python functionality

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def sample_config():
    """Return a sample configuration dictionary for testing."""
    return {
        "ai_provider": "gemini",
        "max_crawl_steps": 15,
        "max_crawl_duration_seconds": 600,
    }
```

**Location:**
- `conftest.py` for shared fixtures
- Test-specific fixtures in individual files
- No dedicated factory modules

## Coverage

**Requirements:**
- Configured to track `mobile_crawler` package
- Missing coverage reports displayed in terminal
- HTML coverage report generated
- Target not enforced but reported

**View Coverage:**
```bash
pytest --cov=mobile_crawler --cov-report=term-missing  # Show missing lines
pytest --cov-report=html                               # Generate HTML report
open htmlcov/index.html                                # View report
```

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods
- Isolated from external dependencies
- Mock external services
- Fast execution
- Marked with `@pytest.mark.unit`

**Integration Tests:**
- Scope: Multiple components working together
- May use real databases or minimal mocks
- Test actual integrations
- Slower execution
- Marked with `@pytest.mark.integration`

**E2E Tests:**
- Not currently detected in codebase
- Would test complete user workflows

## Common Patterns

**Async Testing:**
- Limited async usage detected
- Standard pytest async support available if needed

**Error Testing:**
```python
def test_config_set_exception(self, monkeypatch):
    """Test exception handling during config set."""
    with monkeypatch.context() as m:
        m.setattr("mobile_crawler.config.config_manager.logger",
                 Mock(error=Mock(side_effect=Exception("DB Error"))))

        # Verify error is handled gracefully
        result = runner.invoke(cli, ['config', 'set', 'key', 'value'])
        assert result.exit_code == 0  # Command completes despite error
```

**UI Testing:**
- Qt fixtures available in `conftest.py`:
```python
@pytest.fixture(scope="session")
def qt_app():
    """Create QApplication instance for all UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
```

---

*Testing analysis: 2026-04-05*