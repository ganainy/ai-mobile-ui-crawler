# Quickstart: UiAutomator2 Crash Detection and Recovery

**Feature**: 023-uiautomator-crash-recovery  
**Date**: 2026-01-15

## Overview

This document provides a quickstart guide for developing and testing the UiAutomator2 crash recovery feature.

---

## Development Setup

### Prerequisites
- Python 3.11+
- Appium server running (port 4723)
- Android device/emulator connected
- Existing mobile-crawler development environment

### No Additional Dependencies
This feature uses existing dependencies:
- `appium-python-client`
- `selenium`
- `pytest`

---

## Implementation Order

### Phase 1: Core Recovery Logic (Day 1)

1. **Create `uiautomator_recovery.py`**
   ```bash
   # Create new module
   src/mobile_crawler/core/uiautomator_recovery.py
   ```
   
   Implement:
   - `UIAUTOMATOR2_CRASH_PATTERNS` constant
   - `is_uiautomator2_crash(error)` function
   - `RecoveryState` dataclass
   - `UiAutomatorRecoveryManager` class

2. **Modify `appium_driver.py`**
   - Add `restart_uiautomator2()` method (wrapper around `reconnect()`)

### Phase 2: Integration (Day 1-2)

3. **Modify `gesture_handler.py`**
   - Import crash detection function
   - Re-raise crash errors instead of returning False

4. **Modify `action_executor.py`**
   - Handle re-raised crash exceptions
   - Add optional recovery callback

5. **Modify `crawler_loop.py`**
   - Add `_recovery_state` attribute
   - Add `_execute_action_with_recovery()` method
   - Emit recovery events

### Phase 3: Testing (Day 2)

6. **Create unit tests**
   ```bash
   tests/unit/core/test_uiautomator_recovery.py
   ```

7. **Create integration tests**
   ```bash
   tests/integration/test_crash_recovery.py
   ```

---

## Testing Strategy

### Unit Tests

Test the recovery logic in isolation:

```python
# tests/unit/core/test_uiautomator_recovery.py

def test_is_uiautomator2_crash_detects_instrumentation_error():
    """Crash pattern should be detected."""
    error = WebDriverException("instrumentation process is not running")
    assert is_uiautomator2_crash(error) is True

def test_is_uiautomator2_crash_ignores_regular_error():
    """Regular errors should not trigger recovery."""
    error = WebDriverException("Element not found")
    assert is_uiautomator2_crash(error) is False

def test_recovery_state_should_retry():
    """Should allow retries up to max."""
    state = RecoveryState(max_attempts=3)
    assert state.should_retry() is True
    state.record_attempt(success=False)
    state.record_attempt(success=False)
    state.record_attempt(success=False)
    assert state.should_retry() is False

def test_recovery_state_resets_on_success():
    """Counter should reset after success."""
    state = RecoveryState(max_attempts=3)
    state.record_attempt(success=False)
    state.record_attempt(success=False)
    state.record_attempt(success=True)  # Success resets
    assert state.current_attempts == 0
    assert state.should_retry() is True
```

### Integration Tests

Test recovery with mocked Appium crashes:

```python
# tests/integration/test_crash_recovery.py

@pytest.fixture
def mock_appium_driver():
    """Mock AppiumDriver that simulates crash."""
    driver = Mock(spec=AppiumDriver)
    driver.reconnect = Mock(return_value=Mock())
    return driver

def test_recovery_from_single_crash(mock_appium_driver):
    """Should recover from a single crash and retry action."""
    # First call raises crash error, second succeeds
    mock_gesture = Mock()
    mock_gesture.tap_at = Mock(
        side_effect=[
            WebDriverException("instrumentation process is not running"),
            True  # Success on retry
        ]
    )
    
    executor = ActionExecutor(mock_appium_driver, mock_gesture)
    # ... test recovery flow

def test_recovery_exhausted_after_max_attempts(mock_appium_driver):
    """Should fail after max recovery attempts."""
    mock_gesture = Mock()
    mock_gesture.tap_at = Mock(
        side_effect=WebDriverException("instrumentation process is not running")
    )
    
    # All 3 attempts fail
    # ... verify crawl terminates with appropriate status
```

### Manual Testing

1. **Start a crawl session**
2. **During crawl, kill UiAutomator2 on device:**
   ```bash
   adb shell am force-stop io.appium.uiautomator2.server.test
   ```
3. **Observe:**
   - Recovery log messages appear
   - Crawl continues after recovery
   - Action is retried successfully

---

## Key Code Patterns

### Crash Detection

```python
from mobile_crawler.core.uiautomator_recovery import is_uiautomator2_crash

try:
    result = gesture_handler.tap_at(x, y)
except WebDriverException as e:
    if is_uiautomator2_crash(e):
        # Handle with recovery
        pass
    else:
        # Regular error handling
        raise
```

### Recovery Flow

```python
def _execute_action_with_recovery(self, action, context) -> ActionResult:
    """Execute action with automatic crash recovery."""
    while self._recovery_state.should_retry():
        try:
            return self._execute_single_action(action, context)
        except WebDriverException as e:
            if not is_uiautomator2_crash(e):
                raise
            
            self._recovery_state.record_attempt(success=False)
            self._emit_event("on_recovery_started", ...)
            
            if self._recovery_state.should_retry():
                success = self._attempt_restart()
                self._emit_event("on_recovery_completed", ..., success)
                if success:
                    continue
            
            break
    
    self._emit_event("on_recovery_exhausted", ...)
    return ActionResult(success=False, error_message="Recovery exhausted")
```

### Event Integration (UI)

```python
# In CrawlControlPanel or log panel
def on_recovery_started(self, run_id, step, attempt, max_attempts):
    self._log_message(
        f"⚠️ UiAutomator2 crash detected. Recovering... "
        f"(attempt {attempt}/{max_attempts})"
    )

def on_recovery_completed(self, run_id, step, success, duration_ms):
    if success:
        self._log_message(f"✅ Recovery successful ({duration_ms:.0f}ms)")
    else:
        self._log_message(f"❌ Recovery failed, retrying...")
```

---

## Configuration

### Default Values

| Setting | Default | Description |
|---------|---------|-------------|
| `uiautomator2_max_recovery_attempts` | 3 | Max restart attempts per step |
| `uiautomator2_recovery_delay` | 3.0 | Seconds to wait after restart |

### Setting via ConfigManager

```python
# In config_manager settings or UI
config_manager.set("uiautomator2_max_recovery_attempts", 5)
config_manager.set("uiautomator2_recovery_delay", 5.0)
```

---

## Troubleshooting

### Recovery Always Fails

1. Check Appium server logs for session errors
2. Verify device is still connected: `adb devices`
3. Check if target app is still installed
4. Try manual session restart in Appium Inspector

### Too Many False Positives

If non-crash errors trigger recovery:
1. Check error message matches patterns exactly
2. Add logging to see actual error messages
3. Adjust `UIAUTOMATOR2_CRASH_PATTERNS` if needed

### Recovery Too Slow

If 30-second target is exceeded:
1. Reduce `uiautomator2_recovery_delay`
2. Check device performance
3. Consider parallel app reactivation

---

## Files Changed Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `src/mobile_crawler/core/uiautomator_recovery.py` | **NEW** | Recovery manager and utilities |
| `src/mobile_crawler/core/crawler_loop.py` | MODIFY | Add recovery integration |
| `src/mobile_crawler/infrastructure/appium_driver.py` | MODIFY | Add restart method |
| `src/mobile_crawler/infrastructure/gesture_handler.py` | MODIFY | Propagate crash errors |
| `src/mobile_crawler/domain/action_executor.py` | MODIFY | Handle crash exceptions |
| `src/mobile_crawler/domain/models.py` | MODIFY | Extend ActionResult |
| `tests/unit/core/test_uiautomator_recovery.py` | **NEW** | Unit tests |
| `tests/integration/test_crash_recovery.py` | **NEW** | Integration tests |
