# Data Model: UiAutomator2 Crash Detection and Recovery

**Feature**: 023-uiautomator-crash-recovery  
**Date**: 2026-01-15

## Overview

This document defines the data structures and entities used for UiAutomator2 crash detection and recovery.

---

## Entities

### RecoveryConfig

Configuration for crash recovery behavior.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_restart_attempts` | int | 3 | Maximum recovery attempts per step |
| `restart_delay_seconds` | float | 3.0 | Delay after restart before retry |
| `emit_events` | bool | True | Whether to emit UI events |

**Location**: `config_manager` settings or constructor parameter

**Usage**:
```python
recovery_config = RecoveryConfig(
    max_restart_attempts=3,
    restart_delay_seconds=3.0,
    emit_events=True
)
```

---

### RecoveryState

Tracks recovery attempts within a crawl step. Non-persistent (in-memory only).

| Field | Type | Description |
|-------|------|-------------|
| `current_attempts` | int | Number of restart attempts in current step |
| `max_attempts` | int | Maximum allowed attempts (from config) |
| `delay_seconds` | float | Delay between attempts (from config) |
| `last_recovery_time` | Optional[datetime] | Timestamp of last recovery attempt |
| `last_error_message` | Optional[str] | Error from last failed attempt |

**Lifecycle**:
- Created when crawl starts
- Incremented on each recovery attempt
- Reset to 0 on successful action execution
- Reset to 0 at start of each new step

**Methods**:
| Method | Return | Description |
|--------|--------|-------------|
| `should_retry()` | bool | True if attempts < max_attempts |
| `record_attempt(success: bool)` | None | Increment or reset counter |
| `reset()` | None | Reset counter to 0 |

---

### RecoveryResult

Result of a recovery attempt. Returned by recovery manager.

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Whether UiAutomator2 was successfully restarted |
| `attempt_number` | int | Which attempt this was (1-indexed) |
| `duration_ms` | float | Time taken for recovery attempt |
| `error_message` | Optional[str] | Error if recovery failed |

---

### ActionResult (Extended)

The existing `ActionResult` model in `domain/models.py` needs extension.

**New Fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `was_retried` | bool | False | True if action was retried after recovery |
| `retry_count` | int | 0 | Number of retries before success/failure |
| `recovery_time_ms` | Optional[float] | None | Total time spent in recovery |

**Backward Compatible**: Existing code that doesn't use these fields will work unchanged.

---

## Error Patterns

### UIAUTOMATOR2_CRASH_PATTERNS

A constant list of string patterns that identify UiAutomator2 crashes.

```python
UIAUTOMATOR2_CRASH_PATTERNS: List[str] = [
    "instrumentation process is not running",
    "cannot be proxied to UiAutomator2 server",
    "UiAutomator2 server is not running",
    "session is either terminated or not started",
    "UiAutomator2 is not available",
]
```

**Usage**: Case-insensitive substring matching against exception messages.

---

## Events

Events emitted during recovery for UI feedback.

### on_recovery_started

Emitted when crash recovery begins.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | int | Current run ID |
| `step_number` | int | Current step number |
| `attempt_number` | int | Which attempt (1-indexed) |
| `max_attempts` | int | Maximum attempts configured |
| `action_type` | str | Type of action that triggered crash |

### on_recovery_completed

Emitted when a recovery attempt finishes.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | int | Current run ID |
| `step_number` | int | Current step number |
| `success` | bool | Whether recovery succeeded |
| `duration_ms` | float | Time taken for recovery |

### on_recovery_exhausted

Emitted when max retries are exhausted.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | int | Current run ID |
| `step_number` | int | Step where recovery failed |
| `total_attempts` | int | Total attempts made |
| `error_message` | str | Final error message |

---

## State Diagram

```
                    ┌─────────────────┐
                    │  Action Start   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
              ┌────►│ Execute Action  │
              │     └────────┬────────┘
              │              │
              │     ┌────────┴────────┐
              │     │                 │
              │     ▼                 ▼
              │ ┌───────┐      ┌──────────────┐
              │ │Success│      │   Failure    │
              │ └───┬───┘      └──────┬───────┘
              │     │                 │
              │     ▼                 ▼
              │ ┌───────┐      ┌──────────────┐
              │ │ Reset │      │ Is UA2 Crash?│
              │ │ State │      └──────┬───────┘
              │ └───┬───┘             │
              │     │         ┌───────┴───────┐
              │     │         │               │
              │     │         ▼               ▼
              │     │    ┌────────┐      ┌────────┐
              │     │    │  Yes   │      │   No   │
              │     │    └────┬───┘      └────┬───┘
              │     │         │               │
              │     │         ▼               ▼
              │     │  ┌──────────────┐  ┌────────┐
              │     │  │ Can Retry?   │  │ Return │
              │     │  └──────┬───────┘  │ Error  │
              │     │         │          └────────┘
              │     │  ┌──────┴──────┐
              │     │  │             │
              │     │  ▼             ▼
              │     │ Yes           No
              │     │  │             │
              │     │  ▼             ▼
              │     │ ┌─────────┐  ┌─────────────┐
              └─────┼─┤ Restart │  │  Terminate  │
                    │ │   UA2   │  │   Crawl     │
                    │ └─────────┘  └─────────────┘
                    │
                    ▼
               ┌─────────┐
               │  Done   │
               └─────────┘
```

---

## Database Changes

**None required.** 

Recovery state is transient (in-memory only). If future requirements need recovery history logging, consider adding a `recovery_events` table:

```sql
-- FUTURE: Not implemented in this feature
CREATE TABLE recovery_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    attempt_number INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    duration_ms REAL,
    error_message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);
```
