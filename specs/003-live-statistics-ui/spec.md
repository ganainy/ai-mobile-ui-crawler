# Feature Specification: Live Statistics Dashboard Updates

**Feature Branch**: `003-live-statistics-ui`  
**Created**: January 11, 2026  
**Status**: Draft  
**Input**: User description: "statistics ui doesnt update with the run and stays like the picture so we need to make it work and add other statics to it as you see fit"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real-time Statistics Updates (Priority: P1)

Users need to see live statistics update during a crawl session to monitor progress and make informed decisions about whether to continue, stop, or adjust the crawl. Currently, the statistics panel remains static with zero values throughout the entire crawl.

**Why this priority**: This is the core functionality needed for effective crawl monitoring. Without live updates, users cannot track crawl progress or identify issues until completion, making the statistics dashboard essentially non-functional.

**Independent Test**: Can be fully tested by starting a crawl and verifying that statistics (steps, screens, AI calls) update in real-time as the crawler executes, delivering immediate visibility into crawl progress.

**Acceptance Scenarios**:

1. **Given** a crawl is running, **When** the crawler completes a step, **Then** the total steps count increments by 1 within 1 second
2. **Given** a crawl is running, **When** the crawler visits a new unique screen, **Then** the unique screens count increments immediately
3. **Given** a crawl is running, **When** an AI call is made, **Then** the AI calls count increments and average response time updates
4. **Given** a crawl is running, **When** time elapses, **Then** the elapsed time counter updates every second
5. **Given** a crawl is running, **When** steps or time progress occurs, **Then** the respective progress bars update to reflect current completion percentage
6. **Given** a crawl completes or stops, **When** the user views the statistics, **Then** all statistics display final accurate values from the completed run

---

### User Story 2 - Success/Failure Rate Tracking (Priority: P2)

Users need visibility into how many steps succeed versus fail to assess crawl quality and identify problematic patterns or bugs in the application being tested.

**Why this priority**: Understanding success/failure rates helps users determine if the crawl is productive or if the application has issues. This is valuable but secondary to basic progress tracking.

**Independent Test**: Can be tested independently by running a crawl with intentional failures (e.g., targeting non-existent elements) and verifying the successful/failed step counters update correctly.

**Acceptance Scenarios**:

1. **Given** a crawl is running, **When** a step completes successfully, **Then** the successful steps counter increments
2. **Given** a crawl is running, **When** a step fails, **Then** the failed steps counter increments
3. **Given** the statistics display, **When** viewing step counts, **Then** successful + failed always equals total steps

---

### User Story 3 - Screen Discovery Metrics (Priority: P2)

Users want to track how efficiently the crawler discovers new screens versus revisiting known screens to understand coverage and crawl effectiveness.

**Why this priority**: This helps assess crawl coverage and efficiency, but is less critical than basic progress tracking. Users can still monitor basic progress without these metrics.

**Independent Test**: Can be tested by running a crawl and verifying that unique screens count increases when new screens are discovered, while total visits count increases on every screen visit including revisits.

**Acceptance Scenarios**:

1. **Given** a crawl discovers a new screen, **When** the screen is visited for the first time, **Then** unique screens count increments by 1
2. **Given** a crawl revisits a known screen, **When** the screen is visited again, **Then** unique screens stays the same but total visits increments
3. **Given** elapsed time is tracked, **When** calculating discovery rate, **Then** screens per minute updates based on unique screens divided by elapsed minutes

---

### User Story 4 - AI Performance Monitoring (Priority: P3)

Users want to monitor AI API performance including call counts and average response times to understand AI service costs, latency, and identify performance bottlenecks.

**Why this priority**: This is useful for cost tracking and performance optimization but not essential for basic crawl monitoring. Users can complete successful crawls without this information.

**Independent Test**: Can be tested by making AI calls during a crawl and verifying that the AI calls counter and average response time display update accurately after each call.

**Acceptance Scenarios**:

1. **Given** an AI call completes, **When** response time is recorded, **Then** average response time recalculates as a running average of all calls
2. **Given** multiple AI calls occur, **When** viewing AI statistics, **Then** the average response time reflects the mean of all response times
3. **Given** AI statistics are displayed, **When** response time is shown, **Then** it displays in milliseconds with 0 decimal places for readability

---

### User Story 5 - Statistics Reset and Persistence (Priority: P3)

Users need statistics to reset to zero when starting a new crawl and optionally preserve statistics from previous runs for comparison.

**Why this priority**: This prevents confusion between different crawl sessions but is a supporting feature that doesn't affect core monitoring functionality.

**Independent Test**: Can be tested by completing a crawl, then starting a new crawl and verifying all statistics reset to zero at the start of the new session.

**Acceptance Scenarios**:

1. **Given** statistics show values from a previous crawl, **When** a new crawl starts, **Then** all statistics reset to zero/initial values
2. **Given** a crawl is stopped mid-execution, **When** a new crawl starts, **Then** statistics reset regardless of previous completion state
3. **Given** user wants to compare runs, **When** viewing run history, **Then** final statistics from completed runs are preserved and accessible

---

### Edge Cases

- What happens when statistics update faster than the UI can render (e.g., very rapid steps)? → Updates should be batched or throttled to avoid UI performance issues
- How does the system handle very long-running crawls with large numbers (e.g., 10,000+ steps)? → All counters should support large integers without overflow or display issues
- What happens when progress exceeds configured max values (e.g., steps exceed max_steps limit)? → Progress bars should cap at 100% and display values should continue to increment
- How does the system handle AI calls that timeout or fail? → Failed AI calls should still increment the call counter but may affect average response time calculation
- What happens if database queries for statistics are slow? → UI should remain responsive with last known values while updates occur asynchronously
- How are fractional values handled (e.g., screens per minute with decimals)? → Display should show 1 decimal place for rates/averages

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST emit events during crawl execution for each statistic-relevant occurrence (step completion, screen visit, AI call, etc.)
- **FR-002**: Statistics dashboard MUST subscribe to crawl execution events and update displayed values in response
- **FR-003**: Statistics MUST update within 1 second of the corresponding event occurring during the crawl
- **FR-004**: System MUST track total steps, successful steps, and failed steps independently
- **FR-005**: System MUST track unique screens discovered and total screen visits separately
- **FR-006**: System MUST calculate screens per minute as unique screens divided by elapsed time in minutes
- **FR-007**: System MUST track number of AI API calls and calculate running average of response times
- **FR-008**: System MUST update elapsed time counter every second while crawl is active
- **FR-009**: Progress bars MUST update to show percentage completion for both steps (current/max) and time (elapsed/max)
- **FR-010**: System MUST reset all statistics to zero/initial values when a new crawl starts
- **FR-011**: Statistics updates MUST occur on the main UI thread to ensure thread-safe rendering
- **FR-012**: System MUST query database repositories for final accurate statistics on crawl completion as a validation step
- **FR-013**: System MUST preserve final statistics in database when crawl completes for historical viewing
- **FR-014**: Statistics display MUST remain responsive even during rapid update events
- **FR-015**: System MUST handle progress values exceeding configured maximums gracefully (cap progress bars at 100%, continue incrementing displays)

### Key Entities *(include if feature involves data)*

- **CrawlStatistics**: Aggregated metrics for a crawl session including step counts, screen counts, AI metrics, and duration
- **StepResult**: Individual step outcome (success/failure) that contributes to success/failure tracking
- **ScreenVisit**: Record of screen access including whether it's a unique discovery or revisit
- **AICallMetric**: Individual AI API call record including response time for averaging
- **StatisticsSnapshot**: Point-in-time capture of all statistics values for display updates

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Statistics dashboard updates within 1 second of each crawl event (step completion, screen visit, AI call)
- **SC-002**: Users can monitor real-time crawl progress without needing to check logs or wait for completion
- **SC-003**: All displayed statistics match actual crawl execution data with 100% accuracy at crawl completion
- **SC-004**: UI remains responsive (no freezing or lag) during statistics updates even with update rates up to 10 updates per second
- **SC-005**: Users can distinguish between productive crawls (high unique screen discovery) and inefficient crawls (high revisit rates) by viewing screen discovery metrics
- **SC-006**: Users can identify AI performance issues (slow response times, excessive calls) during execution rather than after completion
- **SC-007**: Statistics correctly reset to zero when starting a new crawl, preventing confusion between sessions
- **SC-008**: Progress bars accurately reflect completion percentage and help users estimate time remaining

## Assumptions

- The existing event system (signal_adapter with signals like step_completed) can be extended or modified to emit statistics-relevant events
- Database repositories (run_repository, step_log_repository, screen_repository) contain methods to query aggregated statistics
- The StatsDashboard widget's update_stats() method signature is sufficient for all required statistics
- Statistics updates should be real-time priority over batch efficiency (users value immediate feedback)
- The existing max_steps and max_duration_seconds configuration is available from settings or crawl configuration
- Screen "uniqueness" is determined by existing screen identifier logic in the screen repository
- AI response times are recorded somewhere in the system (likely in AI interaction service or step logs)
- The Qt signal/slot mechanism is the appropriate pattern for thread-safe communication between crawler and UI

## Scope

### In Scope

- Implementing event emissions from crawler components to signal statistics changes
- Wiring statistics events to StatsDashboard update methods
- Adding timers or periodic updates for elapsed time tracking
- Querying database repositories for accurate statistics aggregation
- Ensuring thread-safe statistics updates via Qt signals
- Testing real-time update behavior during active crawls
- Resetting statistics when new crawls start

### Out of Scope

- Adding entirely new statistics types beyond what's already in StatsDashboard UI structure
- Historical statistics comparison or charting/graphing features
- Statistics export or reporting functionality
- Performance optimization beyond basic throttling/batching
- Statistics persistence mechanisms (database schema changes)
- Advanced statistics like action type distribution, gesture success rates, or error categorization
- User-configurable statistics refresh rates or display preferences
- Statistics dashboard visual redesign or layout changes

## Dependencies

- Existing CrawlerLoop and CrawlController event emission capabilities
- QtSignalAdapter for thread-safe signal bridging
- RunRepository, ScreenRepository, StepLogRepository for statistics queries
- AIInteractionService for AI call metrics tracking
- Qt QTimer for periodic elapsed time updates

## Notes

- The current implementation shows that signal_adapter already has step_completed signal but it's only used for logging, not statistics updates
- The _on_step_completed method in MainWindow has a comment noting "Full stats update would require accumulating data from run repository" - this indicates awareness of the missing functionality
- StatsDashboard has a complete update_stats() method signature suggesting the UI structure is ready, just not wired to data
- Need to verify if AIInteractionService tracks response times or if this needs to be added
- Should investigate if there's an existing mechanism for periodic updates (QTimer) or if one needs to be created
