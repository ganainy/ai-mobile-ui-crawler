# Feature Specification: AI Input/Output Monitor

**Feature Branch**: `002-ai-io-monitor`  
**Created**: 2026-01-11  
**Status**: Draft  
**Input**: User description: "I want a way so that I can be able to show the AI input and output in the UI to monitor how well my crawler is doing"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Live AI Interactions During Crawl (Priority: P1)

As a crawler operator, I want to see AI prompts and responses in real-time as the crawler runs, so that I can monitor the AI's decision-making process and quickly identify issues.

**Why this priority**: This is the core value of the feature - real-time visibility into AI behavior is essential for understanding crawler performance and debugging issues as they happen.

**Independent Test**: Can be fully tested by starting a crawl and observing AI interactions appear in the monitor panel as each step executes.

**Acceptance Scenarios**:

1. **Given** a crawl is running, **When** the AI receives a prompt, **Then** the prompt content is displayed in the AI monitor panel within 1 second
2. **Given** a crawl is running, **When** the AI returns a response, **Then** the response content (action and reasoning) is displayed in the AI monitor panel within 1 second
3. **Given** the AI monitor panel is visible, **When** multiple AI interactions occur, **Then** they are displayed in chronological order with the newest visible
4. **Given** an AI request fails or times out, **When** the error occurs, **Then** the error message is displayed with visual distinction from successful responses

---

### User Story 2 - Review Historical AI Interactions for a Step (Priority: P2)

As a crawler analyst, I want to review the AI input/output for specific steps in a completed or running crawl, so that I can understand why the crawler made certain decisions.

**Why this priority**: Historical review enables debugging after the fact and learning from crawler behavior patterns.

**Independent Test**: Can be tested by completing a crawl, then selecting a specific step to view its associated AI prompt and response.

**Acceptance Scenarios**:

1. **Given** a crawl has completed or is in progress, **When** I select a specific step, **Then** I can see the AI prompt sent for that step
2. **Given** a step's AI interaction is displayed, **When** viewing the details, **Then** I can see the full response including action and reasoning
3. **Given** multiple steps exist, **When** I navigate between steps, **Then** the AI interaction display updates to show the selected step's data

---

### User Story 3 - Filter and Search AI Interactions (Priority: P3)

As a power user, I want to filter AI interactions by success/failure and search for specific content, so that I can quickly find relevant interactions in long crawl sessions.

**Why this priority**: Filtering and search become valuable for longer crawl sessions but are not essential for basic monitoring.

**Independent Test**: Can be tested by running a crawl with multiple interactions, then using filters to show only failed requests or searching for specific action types.

**Acceptance Scenarios**:

1. **Given** the AI monitor has multiple interactions, **When** I filter by "failed only", **Then** only failed AI interactions are displayed
2. **Given** the AI monitor has multiple interactions, **When** I search for "tap", **Then** only interactions containing "tap" in prompt or response are shown
3. **Given** a filter is active, **When** new interactions arrive, **Then** they are shown or hidden based on current filter settings

---

### Edge Cases

- What happens when the AI response contains extremely long text? → Response should be truncated with "show more" option
- How does the system handle when no AI provider is configured? → Display informative message that AI monitoring is unavailable
- What happens when the database is unavailable? → Show graceful error and continue crawl without logging to monitor
- How does the system handle rapid AI calls (multiple per second)? → Buffer and display without UI lag or dropped entries
- What happens when the user scrolls up while new entries arrive? → Maintain scroll position; new entries don't auto-scroll if user is reviewing history

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display the AI prompt (input) for each crawler step in the UI
- **FR-002**: System MUST display the AI response (output) including action, reasoning, and parsed data
- **FR-003**: System MUST show AI interactions in real-time as the crawler executes (within 1 second)
- **FR-004**: System MUST display error messages when AI requests fail
- **FR-005**: System MUST show performance metrics for each interaction (latency, token counts if available)
- **FR-006**: Users MUST be able to distinguish between successful and failed AI interactions visually
- **FR-007**: System MUST maintain readable performance when displaying 100+ interactions
- **FR-008**: System MUST preserve AI interaction display during and after crawl completion
- **FR-009**: Users MUST be able to expand/collapse long prompt or response content
- **FR-010**: System MUST display timestamp for each AI interaction
- **FR-011**: System MUST allow filtering interactions by success/failure status
- **FR-012**: System MUST allow text search across interaction content

### Key Entities

- **AI Interaction**: A single prompt/response exchange with the AI model; contains request content, response content, timing, success status, error info
- **Monitor Panel**: UI component that displays AI interactions in real-time and supports historical review
- **Interaction Entry**: Visual representation of one AI interaction showing prompt, response, metrics, and status

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can see AI interactions appear in the monitor within 1 second of occurrence
- **SC-002**: The monitor panel can display 100 interactions without noticeable UI lag
- **SC-003**: Users can identify failed interactions within 2 seconds of viewing the panel (visual distinction)
- **SC-004**: 90% of users can understand what action the AI decided to take by reading the monitor entry
- **SC-005**: Users can review any historical step's AI interaction within 3 clicks
- **SC-006**: Filter and search results appear within 500ms of user input

## Assumptions

- The existing `AIInteractionRepository` and `AIInteraction` dataclass provide all necessary data (prompt, response, latency, success, error, tokens)
- The existing `signal_adapter` pattern will be used for thread-safe UI updates from the crawler thread
- The UI is built with PySide6, so the monitor will follow existing widget patterns
- Token counts may not be available for all AI providers (display "N/A" when unavailable)
- The monitor panel will be added to the existing main window layout
