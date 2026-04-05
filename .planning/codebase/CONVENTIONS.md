# Coding Conventions

**Analysis Date:** 2026-04-05

## Naming Patterns

**Files:**
- Lowercase with underscores: `config_manager.py`, `crawl_controller.py`, `main_window.py`
- Test files follow same pattern with `test_` prefix: `test_config_command.py`
- CLI commands: `commands` directory with individual files per command
- Package structure: `mobile_crawler` as root namespace

**Functions:**
- Snake_case for function names: `get_config()`, `crawl_controller()`, `pause()`, `resume()`
- Protected methods use underscore prefix: `_state`, `_notify_state_change()`
- Private methods use double underscore: `__init_private_method()`

**Variables:**
- Snake_case for local variables: `user_config_store`, `max_crawl_steps`
- Instance variables with underscore prefix: `_state`, `_lock`
- Constants in UPPER_SNAKE_CASE: `DEFAULTS` (in `defaults.py`)

**Classes:**
- PascalCase for class names: `CrawlController`, `ConfigManager`, `GeminiAdapter`
- Enum classes follow same pattern: `CrawlControlState`
- Adapters suffixed with "Adapter": `GeminiAdapter`

**Type Hints:**
- Used consistently throughout codebase
- Imports from `typing`: `Optional`, `Dict`, `List`, `Any`, `Callable`
- Complex types defined explicitly: `list[Callable[[CrawlControlState], None]]`

## Code Style

**Formatting:**
- Black formatter with line length 120
- Ruff linter configured with:
  - E: pycodestyle errors
  - W: pycodestyle warnings
  - F: pyflakes
  - I: isort
  - B: flake8-bugbear
  - C4: flake8-comprehensions
  - UP: pyupgrade
- Ignored rules: E501 (line too long), B008 (function calls in args), C901 (too complex)

**Docstrings:**
- Triple quotes for all modules, classes, functions
- Public methods have comprehensive docstrings with Args/Returns sections
- Example from `crawl_controller.py`:
```python
def pause(self) -> None:
    """Pause the crawl.

    If the crawl is running, it will be paused.
    If already paused or stopped, this is a no-op.
    """
```

## Import Organization

**Order:**
1. Standard library imports (top-level)
2. Third-party imports
3. Local application imports (relative imports preferred)
4. Internal module imports

**Example pattern:**
```python
import logging
import threading
from typing import Callable, Optional
from pathlib import Path

import google.genai as genai
from PIL import Image

from mobile_crawler.domain.model_adapters import ModelAdapter
from mobile_crawler.core.crawl_controller import CrawlControlState
```

**Path Aliases:**
- Standard Python path resolution from `src` directory
- No custom path aliases configured

## Error Handling

**Patterns:**
- Graceful degradation when possible (e.g., config fallback)
- Try-except blocks around external dependencies
- Logging with appropriate severity levels
- Custom exceptions not heavily used - prefer return codes/checks

**Example from `config_manager.py`:**
```python
try:
    db_value = self.user_config_store.get_setting(key)
    if db_value is not None:
        return db_value
except Exception as e:
    # If DB access fails, log it and continue to next source
    import logging
    logging.getLogger(__name__).error(f"DB Read Error for key '{key}': {e}", exc_info=True)
    pass
```

**Logging:**
- Standard Python `logging` module used throughout
- Logger name matches module: `logger = logging.getLogger(__name__)`
- Different log levels used appropriately:
  - DEBUG: Detailed tracing
  - INFO: State changes and significant events
  - WARNING: Non-critical issues
  - ERROR: Failures and exceptions

## Comments

**When to Comment:**
- Complex algorithms or business logic
- API boundaries and external integrations
- Non-obvious side effects
- TODO/FIXME items with clear context

**JSDoc/TSDoc:**
- Not used - Python uses docstrings instead
- Docstring format includes Args, Returns, and Examples where appropriate

## Function Design

**Size:**
- Generally small and focused functions
- Methods typically under 50 lines
- Single responsibility principle followed

**Parameters:**
- Type hints used for all parameters
- Default values for optional parameters
- Clear parameter names that indicate purpose

**Return Values:**
- Consistent return types
- Explicit returns rather than implicit None
- Union types for multiple return possibilities

## Module Design

**Exports:**
- Public API clearly defined through `__init__.py` files
- Internal modules prefixed with underscore
- Factory functions and main classes exposed at package level

**Barrel Files:**
- Used for organizing related functionality
- Example: `mobile_crawler/cli/main.py` imports all commands and exposes CLI

---

*Convention analysis: 2026-04-05*