# Event Interface Contract: Operation Timing Events

**Feature**: 025-stats-and-stability  
**Version**: 1.0.0  
**Date**: 2026-01-16

## Overview

This document defines the contract for new timing-related events added to the `CrawlerEventListener` interface.

## Event Definitions

### on_ocr_completed

Emitted after OCR grounding processing completes for a step.

**Signature**:
```python
def on_ocr_completed(
    self,
    run_id: int,
    step_number: int,
    duration_ms: float,
    element_count: int
) -> None
```

**Parameters**:

| Parameter | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| `run_id` | int | Current crawl run ID | > 0 |
| `step_number` | int | Current step number | >= 1 |
| `duration_ms` | float | OCR processing time | >= 0.0 |
| `element_count` | int | Number of text elements detected | >= 0 |

**When Emitted**:
- After `GroundingManager.process_screenshot()` completes successfully
- Before AI request is sent

**Not Emitted When**:
- Grounding/OCR is disabled
- Grounding fails (error logged instead)

---

### on_screenshot_timing

Emitted after screenshot capture completes for a step.

**Signature**:
```python
def on_screenshot_timing(
    self,
    run_id: int,
    step_number: int,
    duration_ms: float
) -> None
```

**Parameters**:

| Parameter | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| `run_id` | int | Current crawl run ID | > 0 |
| `step_number` | int | Current step number | >= 1 |
| `duration_ms` | float | Screenshot capture time | >= 0.0 |

**When Emitted**:
- After `ScreenshotCapture.capture_full()` completes
- Before OCR/grounding begins

**Not Emitted When**:
- Screenshot capture fails (error logged instead)

---

### on_action_executed (Extended)

The existing `on_action_executed` event already includes timing information via the `ActionResult` object.

**Existing Signature**:
```python
def on_action_executed(
    self,
    run_id: int,
    step_number: int,
    action_index: int,
    result: ActionResult
) -> None
```

**ActionResult Fields for Timing**:
- `result.success`: bool - whether action succeeded
- Timing is not currently in ActionResult but can be calculated from step timing

**Proposed Extension to ActionResult**:
```python
@dataclass
class ActionResult:
    success: bool
    action_type: str
    target: str
    error_message: Optional[str] = None
    was_retried: bool = False
    retry_count: int = 0
    recovery_time_ms: float = 0.0
    execution_time_ms: float = 0.0  # NEW FIELD
```

---

## Qt Signal Mappings

| Event | Qt Signal | Signal Signature |
|-------|-----------|------------------|
| `on_ocr_completed` | `ocr_completed` | `Signal(int, int, float, int)` |
| `on_screenshot_timing` | `screenshot_timing` | `Signal(int, int, float)` |

---

## Event Ordering Guarantee

Events for a single step are emitted in this order:

1. `on_step_started(run_id, step_number)`
2. `on_screenshot_captured(run_id, step_number, path)`
3. `on_screenshot_timing(run_id, step_number, duration_ms)` **NEW**
4. `on_ocr_completed(run_id, step_number, duration_ms, elements)` **NEW**
5. `on_ai_request_sent(run_id, step_number, request_data)`
6. `on_ai_response_received(run_id, step_number, response_data)`
7. `on_action_executed(run_id, step_number, action_index, result)` (per action)
8. `on_screen_processed(run_id, step_number, screen_id, is_new, visits, total)`
9. `on_step_completed(run_id, step_number, actions_count, duration_ms)`

---

## Backward Compatibility

- New events have default no-op implementations in base `CrawlerEventListener`
- Existing listeners don't need to implement new methods
- No breaking changes to existing event signatures
