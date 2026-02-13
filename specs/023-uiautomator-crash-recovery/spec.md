# Feature Specification: UiAutomator2 Crash Detection and Recovery

**Feature Branch**: `023-uiautomator-crash-recovery`  
**Created**: 2026-01-15  
**Status**: Draft  
**Input**: User description: "Detect UiAutomator2 crash and restart it, then retry the failed action"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Recovery from UiAutomator2 Crash (Priority: P1)

As a crawler operator, I want the system to automatically detect when UiAutomator2 crashes and recover gracefully, so that my crawl sessions can continue without manual intervention.

**Why this priority**: UiAutomator2 crashes are a critical failure mode that completely blocks all device interactions. Without automatic recovery, the entire crawl fails and requires manual restart, wasting time and resources.

**Independent Test**: Can be fully tested by inducing a UiAutomator2 crash (or mocking the error) during a crawl session and verifying the system automatically recovers and continues the crawl.

**Acceptance Scenarios**:

1. **Given** a crawl is in progress, **When** a UiAutomator2 crash is detected (error message contains "instrumentation process is not running"), **Then** the system should automatically attempt to restart the UiAutomator2 session.

2. **Given** UiAutomator2 has crashed during an action execution, **When** the session is successfully restarted, **Then** the failed action should be automatically retried.

3. **Given** UiAutomator2 has crashed, **When** the restart attempt fails, **Then** the system should log a clear error message and gracefully terminate the crawl with appropriate status.

---

### User Story 2 - Configurable Retry Behavior (Priority: P2)

As a crawler operator, I want to configure the number of restart attempts and retry behavior for UiAutomator2 crash recovery, so that I can balance resilience against infinite loops.

**Why this priority**: Different apps and devices may have different stability characteristics. Configuration allows operators to tune the recovery behavior to their specific needs.

**Independent Test**: Can be tested by configuring different retry limits and verifying the system respects those limits during crash recovery.

**Acceptance Scenarios**:

1. **Given** UiAutomator2 crashes, **When** the configured maximum restart attempts (default: 3) is reached without success, **Then** the crawl should terminate with a "recovery failed" status.

2. **Given** a restart attempt succeeds, **When** the action is retried and succeeds, **Then** the retry counter should reset for subsequent failures.

3. **Given** a restart attempt succeeds, **When** the retried action fails for non-crash reasons, **Then** normal action failure handling should proceed (not counted as crash recovery failure).

---

### User Story 3 - Recovery Visibility and Logging (Priority: P3)

As a crawler operator, I want to see clear logs and UI indicators when crash recovery occurs, so that I can monitor system health and identify problematic apps or devices.

**Why this priority**: Visibility into crash recovery events helps operators diagnose recurring issues and make informed decisions about crawl configurations or device health.

**Independent Test**: Can be tested by triggering a crash recovery scenario and verifying log entries and UI updates are visible.

**Acceptance Scenarios**:

1. **Given** UiAutomator2 crashes during a crawl, **When** recovery is initiated, **Then** a DEBUG log should be emitted: "UiAutomator2 crash detected, attempting restart (attempt N of M)".

2. **Given** recovery succeeds, **When** the action is retried, **Then** a DEBUG log should be emitted: "UiAutomator2 recovered, retrying action: [action_type]".

3. **Given** the crawler UI is visible, **When** a crash recovery event occurs, **Then** the UI should display a transient notification or log entry indicating recovery in progress.

---

### Edge Cases

- What happens when UiAutomator2 crashes repeatedly in quick succession (within the same step)?
- How does the system handle a crash during the restart process itself?
- What happens if the target app is no longer in the foreground after UiAutomator2 restarts?
- How does the system handle a crash during input actions where text has already been partially entered?
- What happens if Appium server itself becomes unresponsive (not just UiAutomator2)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect UiAutomator2 crashes by identifying specific error patterns in action execution failures (e.g., "instrumentation process is not running", "cannot be proxied to UiAutomator2 server").

- **FR-002**: System MUST attempt to restart the UiAutomator2 session when a crash is detected, using the existing Appium session reconnection mechanism.

- **FR-003**: System MUST retry the failed action after a successful UiAutomator2 restart.

- **FR-004**: System MUST enforce a configurable maximum number of restart attempts per crawl step (default: 3).

- **FR-005**: System MUST reset the restart attempt counter upon successful action execution following recovery.

- **FR-006**: System MUST log all crash detection, recovery attempts, and outcomes with appropriate log levels (DEBUG for progress, WARNING for failures, ERROR for unrecoverable situations).

- **FR-007**: System MUST gracefully terminate the crawl if maximum restart attempts are exhausted, updating run status to indicate recovery failure.

- **FR-008**: System MUST ensure the target app is brought back to foreground after UiAutomator2 restart before retrying the action.

- **FR-009**: System MUST emit events to notify UI listeners when crash recovery is in progress (for visual feedback).

### Key Entities

- **CrashRecoveryError**: Represents a detected UiAutomator2 crash condition, containing the original error message and action context.
- **RecoveryAttempt**: Tracks individual restart attempts, including timestamp, attempt number, and outcome (success/failure).
- **RecoveryConfig**: Configuration entity with max_restart_attempts, restart_delay_seconds, and per-step vs per-crawl limits.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Crawls experiencing a single UiAutomator2 crash achieve 95%+ recovery success rate without operator intervention.

- **SC-002**: Recovery from crash detection to action retry completes within 30 seconds.

- **SC-003**: No more than 5% of crawl sessions should fail due to unrecoverable UiAutomator2 crashes (down from current ~100% per-crash failure rate).

- **SC-004**: All crash recovery events are logged with sufficient detail to diagnose recurring issues.

- **SC-005**: Operators can identify crash recovery events in the UI logs within 2 seconds of occurrence.

## Assumptions

- The Appium server itself remains responsive and only the UiAutomator2 instrumentation crashes.
- The existing `AppiumDriver` class has or can expose methods to restart/reconnect the UiAutomator2 session.
- The device remains connected and accessible via ADB during recovery.
- The target app remains installed on the device (not uninstalled or crashed independently).
- A short delay (2-5 seconds) after restart is acceptable to allow UiAutomator2 to reinitialize.
