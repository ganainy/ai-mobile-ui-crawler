# Feature Specification: Wire Up GUI Widgets

**Feature Branch**: `001-wire-gui-widgets`  
**Created**: 2026-01-10  
**Status**: Draft  
**Input**: User description: "Wire up the GUI - Connect existing widgets to main window for a functional UI that allows complete crawl runs with AI"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Launch GUI and Configure AI Provider (Priority: P1)

A user launches the Mobile Crawler GUI application and configures their AI provider (Gemini, OpenRouter, or Ollama) with appropriate API keys before starting a crawl.

**Why this priority**: Without AI configuration, no crawl can execute. This is the foundational setup step.

**Independent Test**: Can be tested by launching the app, selecting a provider, entering API key, and verifying the model list populates.

**Acceptance Scenarios**:

1. **Given** the user launches the GUI, **When** the main window opens, **Then** they see device selector, app selector, AI model selector, crawl controls, log viewer, and stats dashboard
2. **Given** the main window is displayed, **When** the user selects an AI provider from dropdown, **Then** the available vision models populate in the model dropdown
3. **Given** the user has selected a provider, **When** they enter a valid API key, **Then** the system validates connectivity and shows success status

---

### User Story 2 - Select Device and Target App (Priority: P1)

A user selects a connected Android device and chooses a target app to crawl from the installed applications list.

**Why this priority**: Device and app selection are required before any crawl can begin.

**Independent Test**: Can be tested by connecting an Android device, refreshing the device list, selecting a device, and viewing the installed apps.

**Acceptance Scenarios**:

1. **Given** an Android device is connected via ADB, **When** the user clicks refresh devices, **Then** the device appears in the device selector dropdown
2. **Given** a device is selected, **When** the user opens app selector, **Then** they see a list of installed packages on the device
3. **Given** the user selects an app, **When** the selection is confirmed, **Then** the Start Crawl button becomes enabled

---

### User Story 3 - Start and Monitor a Crawl (Priority: P1)

A user starts a crawl and monitors progress in real-time through the log viewer and stats dashboard.

**Why this priority**: This is the core functionality - executing an AI-powered crawl with visibility.

**Independent Test**: Can be tested by configuring all settings and clicking Start Crawl, then observing logs and statistics update in real-time.

**Acceptance Scenarios**:

1. **Given** device, app, and AI are configured, **When** user clicks Start Crawl, **Then** the crawl begins and buttons update (Start disabled, Pause/Stop enabled)
2. **Given** a crawl is running, **When** steps execute, **Then** the log viewer shows real-time action logs with timestamps
3. **Given** a crawl is running, **When** steps complete, **Then** the stats dashboard updates with step count, screen count, and elapsed time

---

### User Story 4 - Pause, Resume, and Stop Crawl (Priority: P2)

A user can pause a running crawl, resume it, or stop it completely at any time.

**Why this priority**: Control over crawl execution is important but secondary to basic crawl functionality.

**Independent Test**: Can be tested by starting a crawl, clicking Pause, observing it stops, clicking Resume, and verifying it continues.

**Acceptance Scenarios**:

1. **Given** a crawl is running, **When** user clicks Pause, **Then** the crawl pauses and Resume button appears
2. **Given** a crawl is paused, **When** user clicks Resume, **Then** the crawl continues from where it left off
3. **Given** a crawl is running or paused, **When** user clicks Stop, **Then** the crawl terminates and final stats are shown

---

### User Story 5 - View Run History (Priority: P3)

A user can view previous crawl runs and their results from the history panel.

**Why this priority**: History viewing is a convenience feature, not required for core functionality.

**Independent Test**: Can be tested by completing a crawl, then viewing the run history list.

**Acceptance Scenarios**:

1. **Given** previous crawls have been completed, **When** user opens run history, **Then** they see a list of past runs with timestamps and status
2. **Given** run history is displayed, **When** user selects a run, **Then** they see summary stats for that run

---

### Edge Cases

- What happens when no Android device is connected? → Device selector shows "No devices found" with refresh button
- What happens when AI API key is invalid? → Status shows error message, Start button remains disabled
- What happens when the target app crashes during crawl? → Error logged, crawl attempts recovery or stops gracefully
- What happens when Appium server is not running? → Error shown with instructions to start Appium
- What happens when network connectivity is lost during AI call? → Retry logic with timeout, error logged

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display all existing UI widgets in the main window layout
- **FR-002**: System MUST connect DeviceSelector to DeviceDetection service for real-time device listing
- **FR-003**: System MUST connect AppSelector to show installed apps on selected device
- **FR-004**: System MUST connect AIModelSelector to ProviderRegistry for provider/model selection
- **FR-005**: System MUST connect CrawlControlPanel buttons to CrawlerLoop start/pause/resume/stop
- **FR-006**: System MUST connect LogViewer to receive and display crawl events in real-time
- **FR-007**: System MUST connect StatsDashboard to show live step count, screen count, and duration
- **FR-008**: System MUST connect SettingsPanel for configuring API keys and crawl parameters
- **FR-009**: System MUST enable Start button only when device, app, and AI provider are configured
- **FR-010**: System MUST persist user settings (API keys, preferences) between sessions
- **FR-011**: System MUST run crawl operations in a background thread to keep UI responsive
- **FR-012**: System MUST handle errors gracefully and display user-friendly messages

### Key Entities

- **MainWindow**: Central container that hosts all widgets in a coherent layout
- **CrawlSession**: Active crawl state including device, app, AI config, and runtime stats
- **Configuration**: User settings including API keys, default parameters, and preferences

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can launch GUI and see all functional panels within 3 seconds
- **SC-002**: User can configure AI provider and start a crawl in under 1 minute
- **SC-003**: Log viewer updates within 500ms of each crawl event
- **SC-004**: Stats dashboard reflects accurate counts matching database records
- **SC-005**: UI remains responsive (no freezing) during active crawl
- **SC-006**: All crawl control operations (start/pause/resume/stop) complete within 2 seconds
