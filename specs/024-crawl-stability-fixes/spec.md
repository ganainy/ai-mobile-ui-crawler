# Feature Specification: Crawl Stability & Observability Fixes

**Feature Branch**: `024-crawl-stability-fixes`  
**Created**: 2026-01-15  
**Status**: Draft  
**Input**: User description: "Bug fixes for crawl stability including MobSF polling timeout, PCAPdroid restart handling, time mode timer bug, graceful stop, OCR statistics, pause timer behavior, and log timestamps"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable MobSF Analysis Completion (Priority: P1)

As a security researcher, I want MobSF analysis to wait long enough for completion so that I don't get timeout errors when analyzing large APKs that take several minutes to process.

**Why this priority**: MobSF analysis failing prematurely means incomplete security analysis results, which defeats the purpose of running the analysis. The logs show analysis taking ~3 minutes for a complex APK, but the system times out after 60 seconds.

**Independent Test**: Can be tested by uploading a large APK and verifying the system waits until MobSF reports completion or an extended timeout (e.g., 10 minutes) is reached.

**Acceptance Scenarios**:

1. **Given** a large APK is uploaded to MobSF, **When** MobSF analysis takes 5 minutes, **Then** the system waits until analysis completes and retrieves results successfully
2. **Given** MobSF analysis is in progress, **When** polling for completion status, **Then** the system polls at reasonable intervals (e.g., every 10-15 seconds) until completion
3. **Given** MobSF analysis exceeds the maximum timeout (e.g., 15 minutes), **When** timeout is reached, **Then** the system logs a clear timeout message and fails gracefully

---

### User Story 2 - Clean PCAPdroid Session Management (Priority: P1)

As a user, I want PCAPdroid to be properly stopped before starting a new crawl session so that I don't get capture conflicts or orphaned PCAP files.

**Why this priority**: PCAPdroid conflicts cause PCAP file not found errors and corrupt network capture data, making traffic analysis unreliable.

**Independent Test**: Can be tested by starting a crawl, interrupting it, then starting a new crawl and verifying PCAPdroid captures correctly.

**Acceptance Scenarios**:

1. **Given** PCAPdroid is currently running from a previous session, **When** a new crawl session starts, **Then** the system stops the existing PCAPdroid capture before starting a new one
2. **Given** a new crawl starts, **When** PCAPdroid status is unknown, **Then** the system sends a stop command as a precaution before starting capture
3. **Given** PCAPdroid is running, **When** the crawl ends, **Then** PCAPdroid is stopped and the PCAP file is properly saved

---

### User Story 3 - Accurate Time-Based Crawl Duration (Priority: P1)

As a user, I want time-based crawls to run for the exact duration I specify so that I get consistent and predictable crawl sessions.

**Why this priority**: Time mode is a core crawl configuration. The bug where 300-second crawls stop at 200 seconds means users cannot rely on the configured duration.

**Independent Test**: Can be tested by setting a 300-second time limit and verifying the crawl runs for the full duration.

**Acceptance Scenarios**:

1. **Given** a crawl is configured for 300 seconds, **When** the crawl runs, **Then** it continues until 300 seconds have elapsed (not 200 seconds)
2. **Given** time mode is selected with N seconds, **When** the timer counts, **Then** elapsed time accurately reflects actual wall-clock time
3. **Given** the configured time is reached, **When** the crawl completes, **Then** the final elapsed time matches the configured duration (within 5 seconds tolerance)

---

### User Story 4 - Graceful Crawl Termination (Priority: P2)

As a user, I want the Stop button to end the crawl session gracefully as if the normal termination criteria were met so that all session data is properly saved and closed.

**Why this priority**: Abrupt stops can leave sessions in inconsistent states, with unsaved data or resources not properly released.

**Independent Test**: Can be tested by clicking Stop during a crawl and verifying all artifacts are properly saved.

**Acceptance Scenarios**:

1. **Given** a crawl is in progress, **When** the user clicks the Stop button, **Then** the crawl ends gracefully as if time/steps ran out
2. **Given** the Stop button is clicked, **When** the crawl terminates, **Then** all pending data (screenshots, logs, PCAP files) are properly saved
3. **Given** a graceful stop is triggered, **When** cleanup completes, **Then** MobSF analysis and other background tasks complete or are properly cancelled

---

### User Story 5 - Pause-Aware Timer (Priority: P2)

As a user, I want the crawl timer to pause when I pause the crawl (step-by-step mode or pause button) so that paused time doesn't count toward my crawl duration.

**Why this priority**: Users pausing to inspect state shouldn't have that time counted against their crawl budget, especially in time-limited mode.

**Independent Test**: Can be tested by pausing a crawl for 30 seconds and verifying the timer doesn't advance during pause.

**Acceptance Scenarios**:

1. **Given** a crawl is running in time mode, **When** the crawl is paused, **Then** the elapsed time counter stops incrementing
2. **Given** a crawl is in step-by-step mode, **When** waiting for user to click "Next Step", **Then** the timer does not advance between steps
3. **Given** a paused crawl is resumed, **When** the crawl continues, **Then** the timer resumes from where it was paused

---

### User Story 6 - OCR Performance Statistics (Priority: P3)

As a user, I want to see average OCR operation time in the statistics so that I can understand the performance characteristics of my crawl sessions.

**Why this priority**: OCR performance visibility helps users understand session timing and identify performance bottlenecks.

**Independent Test**: Can be tested by running a crawl and verifying average OCR time appears in statistics.

**Acceptance Scenarios**:

1. **Given** OCR operations are performed during crawl, **When** viewing statistics, **Then** the average OCR operation time is displayed
2. **Given** multiple OCR operations occur, **When** average is calculated, **Then** it reflects the mean time across all OCR operations in the session
3. **Given** no OCR operations occurred, **When** viewing statistics, **Then** OCR average time shows "N/A" or "0"

---

### User Story 7 - Timestamped Logs (Priority: P3)

As a user, I want every log message to include a timestamp so that I can correlate events and debug timing issues.

**Why this priority**: Timestamps are essential for debugging and understanding event sequences, especially when correlating with external systems like MobSF.

**Independent Test**: Can be tested by checking any log output and verifying timestamps are present.

**Acceptance Scenarios**:

1. **Given** any log message is emitted, **When** viewing the log, **Then** the message includes a timestamp
2. **Given** logs are being written, **When** formatting timestamps, **Then** they follow a consistent format (e.g., ISO 8601 or similar)
3. **Given** logs from different components, **When** reading logs, **Then** all components use the same timestamp format

---

### Edge Cases

- What happens if MobSF server is completely unresponsive (not just slow)?
- How does the system handle PCAPdroid not being installed on the device?
- What if the user rapidly clicks pause/resume during a crawl?
- How is remaining time calculated if the system clock changes during crawl?
- What happens if Stop is clicked during the middle of an action execution?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST poll MobSF for analysis completion with configurable timeout (default: 10-15 minutes)
- **FR-002**: System MUST poll MobSF at reasonable intervals (every 10-15 seconds) to avoid excessive server load
- **FR-003**: System MUST stop any running PCAPdroid capture before starting a new capture session
- **FR-004**: System MUST send a precautionary stop command to PCAPdroid at crawl start regardless of known state
- **FR-005**: System MUST accurately track elapsed time in time-based crawl mode
- **FR-006**: System MUST use the user-configured time limit, not a hardcoded or incorrectly calculated value
- **FR-007**: System MUST trigger graceful termination when Stop button is clicked, following the same cleanup path as normal termination
- **FR-008**: System MUST pause the elapsed time counter when crawl is paused or in step-by-step waiting state
- **FR-009**: System MUST resume the elapsed time counter when crawl continues after pause
- **FR-010**: System MUST track OCR operation durations and calculate average time
- **FR-011**: System MUST display average OCR operation time in crawl statistics
- **FR-012**: System MUST include a timestamp in every log message
- **FR-013**: System MUST use a consistent timestamp format across all log sources

### Key Entities

- **CrawlSession**: Tracks elapsed time, pause state, and termination status
- **MobSFManager**: Handles APK analysis with extended polling and timeout configuration
- **PCAPdroidManager**: Manages traffic capture lifecycle with explicit stop-before-start behavior
- **StatisticsCollector**: Accumulates performance metrics including OCR timings
- **Logger**: Emits timestamped log messages

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: MobSF analysis for APKs taking up to 10 minutes completes successfully without timeout errors
- **SC-002**: Zero PCAP file conflicts or "file not found" errors when starting new crawl sessions
- **SC-003**: Time-based crawls run for 100% of the configured duration (within 5-second tolerance)
- **SC-004**: Stop button results in all session artifacts being properly saved with no data loss
- **SC-005**: Paused crawls show 0 seconds advancement in elapsed time counter during pause
- **SC-006**: OCR average time is visible in statistics panel after crawl completion
- **SC-007**: 100% of log messages include timestamps in consistent format
