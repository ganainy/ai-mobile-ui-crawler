# Research: UiAutomator2 Crash Detection and Recovery

**Feature**: 023-uiautomator-crash-recovery  
**Date**: 2026-01-15

## Research Summary

This document captures research findings for implementing UiAutomator2 crash detection and recovery in the mobile-crawler application.

---

## R1: UiAutomator2 Crash Detection Patterns

### Decision
Detect crashes by matching specific error message patterns in WebDriverException errors.

### Rationale
UiAutomator2 crashes produce consistent error patterns that can be reliably detected:
- `"instrumentation process is not running"`
- `"cannot be proxied to UiAutomator2 server"`
- `"UiAutomator2 server is not running"`

These patterns appear in the Appium error response when the UiAutomator2 instrumentation process crashes on the device.

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Health check polling | Adds latency and complexity; reactive detection is simpler |
| Appium server-side detection | Not exposed via client API |
| ADB process monitoring | Overly complex; error matching is sufficient |

### Implementation Pattern
```python
UIAUTOMATOR2_CRASH_PATTERNS = [
    "instrumentation process is not running",
    "cannot be proxied to UiAutomator2 server",
    "UiAutomator2 server is not running",
    "session is either terminated or not started",
]

def is_uiautomator2_crash(error: Exception) -> bool:
    error_msg = str(error).lower()
    return any(pattern.lower() in error_msg for pattern in UIAUTOMATOR2_CRASH_PATTERNS)
```

---

## R2: UiAutomator2 Restart Mechanism

### Decision
Use Appium session reconnection via `AppiumDriver.reconnect()` to restart UiAutomator2.

### Rationale
The existing `reconnect()` method in `AppiumDriver` already handles:
1. Disconnecting the current (crashed) session
2. Creating a new WebDriver session with the same capabilities
3. UiAutomator2 automatically reinitializes when a new session starts

No direct UiAutomator2-specific restart is needed; Appium handles this implicitly.

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| ADB shell restart of UiAutomator2 | Complex, requires direct APK management |
| Appium server restart | Too drastic; only UiAutomator2 crashed |
| New driver instance | Loses session context; reconnect preserves config |

### Key Findings
- `driver.quit()` + new session = UiAutomator2 restart
- Existing `reconnect()` does exactly this
- Need to add delay (2-3 seconds) after reconnect for UiAutomator2 to fully initialize
- Must re-activate target app after restart (use `_ensure_app_foreground()`)

---

## R3: Retry Strategy and State Management

### Decision
Implement a step-scoped retry with configurable maximum attempts (default: 3).

### Rationale
- Per-step retry prevents infinite loops while allowing recovery
- Resetting counter on success allows recovery from intermittent failures
- 3 attempts provides good balance between resilience and timeout prevention

### State Management
```python
class RecoveryState:
    """Tracks recovery attempts within a crawl step."""
    
    def __init__(self, max_attempts: int = 3, delay_seconds: float = 3.0):
        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds
        self.current_attempts = 0
        self.last_recovery_timestamp: Optional[datetime] = None
    
    def should_retry(self) -> bool:
        return self.current_attempts < self.max_attempts
    
    def record_attempt(self, success: bool) -> None:
        if success:
            self.current_attempts = 0  # Reset on success
        else:
            self.current_attempts += 1
        self.last_recovery_timestamp = datetime.now()
    
    def reset_for_new_step(self) -> None:
        self.current_attempts = 0
```

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Global (per-crawl) retry limit | Too restrictive; one bad step could exhaust all retries |
| Unlimited retries | Risk of infinite loops |
| Exponential backoff | Overly complex for this use case; fixed delay sufficient |

---

## R4: Integration Points in Existing Code

### Decision
Integrate recovery logic in `CrawlerLoop._execute_step()` around action execution.

### Rationale
The `_execute_step()` method is the central point where actions are executed. Wrapping action execution with recovery logic provides:
- Centralized recovery handling
- Access to action context for retry
- Minimal changes to existing code

### Integration Pattern

```python
# In CrawlerLoop._execute_step()
for i, ai_action in enumerate(ai_response.actions):
    result = self._execute_action_with_recovery(ai_action, grounding_overlay)
    # ... existing result handling

def _execute_action_with_recovery(self, action, grounding_overlay) -> ActionResult:
    """Execute action with crash recovery retry logic."""
    while self._recovery_state.should_retry():
        try:
            result = self._execute_single_action(action, grounding_overlay)
            if result.success or not self._is_crash_error(result):
                self._recovery_state.reset_for_new_step()
                return result
            # Non-crash failure, return as-is
            return result
        except Exception as e:
            if self._is_uiautomator2_crash(e):
                self._recovery_state.record_attempt(success=False)
                if self._recovery_state.should_retry():
                    self._attempt_recovery()
                    continue
            raise
    # Max retries exhausted
    return ActionResult(success=False, error_message="Max recovery attempts exceeded")
```

### Key Files Modified
1. `crawler_loop.py` - Add recovery wrapper and event emission
2. `appium_driver.py` - Add `restart_uiautomator2()` convenience method
3. `action_executor.py` - Propagate crash errors (not just return False)

---

## R5: Event Emission for UI Feedback

### Decision
Emit recovery events using existing `_emit_event()` pattern in CrawlerLoop.

### Rationale
The crawler already uses `_emit_event()` for UI updates. Adding recovery events follows the established pattern.

### New Events

| Event | Parameters | When Emitted |
|-------|------------|--------------|
| `on_recovery_started` | run_id, step_number, attempt_number, max_attempts | Recovery initiated |
| `on_recovery_completed` | run_id, step_number, success | Recovery attempt finished |
| `on_recovery_failed` | run_id, step_number, error_message | Max retries exhausted |

### UI Integration
The UI can listen for these events in `CrawlControlPanel` to show transient notifications or update the log panel.

---

## R6: Error Propagation in Gesture Handler

### Decision
Modify gesture methods to raise exceptions for crash errors instead of returning False.

### Rationale
Currently, `gesture_handler.tap_at()` catches `WebDriverException` and returns `False`. This loses the error context needed to detect UiAutomator2 crashes.

### Change Required
```python
# Before (gesture_handler.py)
except WebDriverException as e:
    logger.error(f"Failed to tap at ({x}, {y}): {e}")
    return False

# After
except WebDriverException as e:
    if self._is_uiautomator2_crash(e):
        raise  # Let caller handle recovery
    logger.error(f"Failed to tap at ({x}, {y}): {e}")
    return False
```

### Impact
- Requires adding crash detection to gesture_handler
- ActionExecutor must handle raised exceptions
- Backward compatible (non-crash errors still return False)

---

## Resolved Unknowns

| Unknown | Resolution |
|---------|------------|
| How to detect crash? | Error message pattern matching |
| How to restart UiAutomator2? | Use existing `reconnect()` method |
| Where to add retry logic? | `CrawlerLoop._execute_step()` |
| How to track retry state? | Per-step `RecoveryState` object |
| How to notify UI? | Existing `_emit_event()` pattern |
| What happens to partially entered text? | Accept data loss; recovery doesn't attempt to restore |

---

## Next Steps

1. Create `data-model.md` with recovery entities
2. Create `quickstart.md` with testing approach
3. Generate tasks via `/speckit.tasks`
