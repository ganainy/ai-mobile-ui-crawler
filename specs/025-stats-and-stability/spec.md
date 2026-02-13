# Feature Specification: Statistics Display and Crawl Stability Improvements

**Feature Branch**: `025-stats-and-stability`  
**Created**: 2026-01-16  
**Status**: Draft  
**Input**: User description: "OCR average time should show in statistics tab not just as log. Average time for action execution should show in UI. Any operations that take significant time should show in the statistics UI. Crawl finished in 98.8 seconds when set to 300 seconds. PCAPdroid permission screen showed up when crawler finished although API key is provided."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View OCR Processing Time in Statistics (Priority: P1)

As a user, I want to see the average OCR processing time displayed in the Statistics panel so that I can understand how much time is being spent on text recognition during the crawl.

**Why this priority**: OCR processing is a significant time consumer during crawls, and users need real-time visibility into this metric to understand performance bottlenecks.

**Independent Test**: Can be fully tested by starting a crawl and observing that the OCR Avg metric appears in the Statistics panel and updates in real-time.

**Acceptance Scenarios**:

1. **Given** a crawl is running with OCR processing active, **When** the Statistics tab is viewed, **Then** an "OCR Avg: Xms" metric is displayed and updates as new OCR operations complete.
2. **Given** a crawl has completed, **When** viewing the crawl completion log, **Then** the final OCR average is shown both in the log AND in the Statistics panel.

---

### User Story 2 - View Action Execution Timing in Statistics (Priority: P1)

As a user, I want to see the average action execution time in the Statistics panel so that I can understand how quickly the crawler is interacting with the app.

**Why this priority**: Action execution timing directly affects crawl throughput and is essential for diagnosing slow crawls.

**Independent Test**: Can be fully tested by running a crawl with multiple actions and verifying the "Avg Action: Xms" metric updates in the Statistics panel.

**Acceptance Scenarios**:

1. **Given** actions are being executed during a crawl, **When** viewing the Statistics tab, **Then** an "Avg Action: Xms" metric is displayed showing the average action execution time.
2. **Given** multiple action types are executed (tap, swipe, type), **When** viewing statistics, **Then** the average correctly reflects all action types.

---

### User Story 3 - View Timing Breakdown for Operations (Priority: P2)

As a user, I want to see a breakdown of time spent on significant operations so that I can identify which parts of the crawl process are consuming the most time.

**Why this priority**: Understanding time distribution helps users optimize their crawl configuration and identify performance issues.

**Independent Test**: Can be tested by running a crawl and verifying each timed operation category appears in the Statistics panel with realistic values.

**Acceptance Scenarios**:

1. **Given** a crawl is running, **When** viewing the Statistics tab, **Then** I see timing metrics for the following categories:
   - OCR Average Time  
   - AI Response Time (already exists)
   - Action Execution Average
   - Screenshot Capture Average

2. **Given** a crawl has completed, **When** reviewing final statistics, **Then** all timing metrics reflect accurate averages over the entire crawl session.

---

### User Story 4 - Crawl Respects Configured Duration Limit (Priority: P1)

As a user, I want the crawl to run for the full duration I configured (up to the limit) unless it completes all tasks or encounters an error, so that my crawls don't stop prematurely.

**Why this priority**: Users configure duration limits with specific expectations. Early termination without clear cause is confusing and reduces crawl effectiveness.

**Independent Test**: Can be tested by starting a crawl with a 300-second limit on an app with many screens and verifying it runs for approximately 300 seconds.

**Acceptance Scenarios**:

1. **Given** a crawl is configured with a 300-second duration limit, **When** the crawl is running on an app with sufficient content, **Then** the crawl runs for approximately 300 seconds (±5 seconds) before stopping with reason "Duration limit reached".
2. **Given** a crawl duration limit is set, **When** the crawler achieves its goal before the limit, **Then** it stops early with an appropriate reason (e.g., "Goal achieved", "No more actions available").
3. **Given** a crawl stops early, **When** viewing the completion log, **Then** the reason for early termination is clearly stated.

---

### User Story 5 - PCAPdroid Capture Starts Without Permission Prompt (Priority: P2)

As a user, I want the PCAPdroid traffic capture to start automatically without showing a permission prompt when I have provided the API key, so that the crawl is not interrupted.

**Why this priority**: Permission prompts during crawl disrupt automation and can cause the crawler to interact with the wrong app.

**Independent Test**: Can be tested by configuring PCAPdroid API key, starting a crawl with traffic capture enabled, and verifying no permission dialog appears.

**Acceptance Scenarios**:

1. **Given** PCAPdroid API key is configured in Settings, **When** a crawl starts with traffic capture enabled, **Then** PCAPdroid starts capture in the background without showing any permission dialog.
2. **Given** PCAPdroid API key is NOT configured, **When** traffic capture is enabled, **Then** the user is warned that API key is required for non-interactive capture before the crawl starts.
3. **Given** the PCAPdroid app is not installed, **When** traffic capture is enabled, **Then** the user is warned that PCAPdroid needs to be installed.

---

### User Story 6 - Video Recording Starts Successfully (Priority: P2)

As a user, I want video recording to start successfully when enabled, so that I can review crawl sessions visually.

**Why this priority**: Video recording provides valuable debugging information and is a core feature that should work reliably.

**Independent Test**: Can be tested by enabling video recording and verifying the recording starts without errors and produces a valid video file.

**Acceptance Scenarios**:

1. **Given** video recording is enabled, **When** a crawl starts, **Then** screen recording begins successfully without errors.
2. **Given** a previous recording session crashed or was interrupted, **When** a new crawl starts with video recording enabled, **Then** the system gracefully handles the cleanup of any stale recording processes.
3. **Given** video recording fails to start, **When** the error is logged, **Then** the crawl continues without video recording (graceful degradation) and the user is informed.

---

### Edge Cases

- What happens when OCR is disabled or not performed on certain steps? (Show "N/A" or skip metric)
- How does the system handle extremely fast operations (<1ms)? (Show "< 1ms" instead of 0)
- What happens if duration tracking starts before all components are initialized? (Buffer timing until initialization complete)
- How does the UI handle updating many metrics simultaneously? (Batch updates to avoid UI flicker)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display average OCR processing time in the Statistics panel during and after crawl.
- **FR-002**: System MUST display average action execution time in the Statistics panel.
- **FR-003**: System MUST display average screenshot capture time in the Statistics panel.
- **FR-004**: System MUST emit OCR timing data through the existing event listener infrastructure.
- **FR-005**: System MUST emit action execution timing data through the event listener infrastructure.
- **FR-006**: System MUST emit screenshot capture timing data through the event listener infrastructure.
- **FR-007**: System MUST respect the configured duration limit and run for the full duration unless a valid completion reason occurs.
- **FR-008**: System MUST clearly log the reason for crawl completion (duration limit, step limit, goal achieved, user stopped, error, no actions available).
- **FR-009**: System MUST start PCAPdroid capture using the API key without triggering permission dialogs when API key is provided.
- **FR-010**: System MUST validate PCAPdroid configuration before crawl start and warn user of issues.
- **FR-011**: System MUST handle video recording initialization gracefully, including cleanup of stale recording processes.
- **FR-012**: System MUST continue crawl operation even if video recording fails to start (graceful degradation).
- **FR-013**: System MUST update Statistics panel in real-time during crawl execution.
- **FR-014**: System MUST calculate running averages efficiently without storing unbounded historical data.

### Key Entities

- **CrawlStatistics**: Extended to include OCR timing, action timing, and screenshot timing averages.
- **OperationTiming**: New concept representing timing data for a specific operation category (OCR, action, screenshot, AI).
- **StatsDashboard**: Extended UI widget to display new timing metrics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view OCR average time in the Statistics panel within 1 second of each OCR operation completing.
- **SC-002**: Users can view action execution average time in the Statistics panel within 1 second of each action completing.
- **SC-003**: Crawl duration matches configured limit within 5 seconds tolerance when no early termination reason exists.
- **SC-004**: PCAPdroid capture starts without permission dialogs when API key is provided (0 dialogs during automated crawl).
- **SC-005**: Video recording starts successfully on first attempt when enabled, or gracefully degrades with clear user notification.
- **SC-006**: Statistics panel displays at least 4 timing metrics: OCR Avg, AI Avg, Action Avg, Screenshot Avg.
- **SC-007**: Users understand why a crawl stopped through clear completion reason text in the log and UI.

## Assumptions

- PCAPdroid API control mode requires the API key to be set in the PCAPdroid app itself, in addition to being provided in mobile-crawler settings.
- Video recording uses Android's built-in screenrecord command via ADB/Appium.
- OCR timing is already being tracked internally; this feature exposes it to the UI.
- The existing event listener infrastructure (QtSignalAdapter, CrawlerEventListener) can be extended to include additional timing data.
- Duration limits are enforced in the CrawlerLoop main loop by checking elapsed time against the configured limit.
