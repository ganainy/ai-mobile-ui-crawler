# Feature Specification: Application Startup Script

**Feature Branch**: `026-startup-script`  
**Created**: 2026-01-18  
**Status**: ✅ Implemented  
**Input**: User description: "Create a script that does what I do manually every time I want to start the app, while also handling if MobSF or Appium is not installed (warning message if not installed is enough, script doesn't have to handle installing)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One-Command Application Launch (Priority: P1)

As a developer, I want to start the entire mobile-crawler application stack with a single command so that I don't have to manually open multiple terminals and run separate commands each time.

**Why this priority**: This is the core value proposition—eliminating the repetitive manual steps of launching three separate processes (MobSF, Appium, Main UI) every time the application needs to run.

**Independent Test**: Can be fully tested by running the startup script and verifying that the main UI application launches successfully. Delivers immediate time savings and reduced friction.

**Acceptance Scenarios**:

1. **Given** all dependencies are installed, **When** the user runs the startup script, **Then** MobSF (Docker container), Appium server, and the main UI application all start in the correct order
2. **Given** all dependencies are installed, **When** the user runs the startup script, **Then** the user sees status messages indicating each component is starting
3. **Given** all components are starting, **When** Appium and MobSF are ready, **Then** the main UI application launches

---

### User Story 2 - Dependency Detection with Warnings (Priority: P1)

As a developer, I want clear warnings when MobSF (Docker) or Appium are not installed so that I understand why certain features may not work and can take action to install them.

**Why this priority**: Critical for first-time users or when setting up on a new machine—without clear feedback, users would be confused about why the application doesn't work properly.

**Independent Test**: Can be tested by running the script on a system without Docker installed and verifying a clear warning is displayed without crashing.

**Acceptance Scenarios**:

1. **Given** Docker is not installed, **When** the user runs the startup script, **Then** a clear warning message is displayed indicating MobSF cannot be started because Docker is missing
2. **Given** Appium (npm/npx) is not available, **When** the user runs the startup script, **Then** a clear warning message is displayed indicating Appium cannot be started because npm/npx is not available
3. **Given** a dependency is missing, **When** the warning is shown, **Then** the script continues to start the remaining components that can be started
4. **Given** a dependency is missing, **When** the warning is shown, **Then** the script suggests how to install the missing dependency (provides helpful guidance)

---

### User Story 3 - Process Management (Priority: P2)

As a developer, I want the startup script to properly manage the background processes so that I can see their output and terminate them cleanly when done.

**Why this priority**: Essential for debugging and proper system hygiene, but secondary to the core launching functionality.

**Independent Test**: Can be tested by starting the script, observing process outputs, then terminating with Ctrl+C and verifying all child processes are stopped.

**Acceptance Scenarios**:

1. **Given** all components are running, **When** the user presses Ctrl+C (SIGINT), **Then** all started processes (MobSF container, Appium server) are properly terminated
2. **Given** the startup script is running, **When** a background process (MobSF or Appium) crashes, **Then** an appropriate error message is displayed
3. **Given** MobSF is already running on port 8000, **When** the script starts, **Then** the script detects this and skips starting a new container (or warns about the conflict)

---

### User Story 4 - Optional Component Startup (Priority: P3)

As a developer, I sometimes want to start only specific components (e.g., just the UI without MobSF) so that I can work on features that don't require all dependencies.

**Why this priority**: Nice-to-have for development flexibility, but most users will want the full stack.

**Independent Test**: Can be tested by running the script with a flag like `--no-mobsf` and verifying only Appium and the UI start.

**Acceptance Scenarios**:

1. **Given** the user wants to skip MobSF, **When** they run the script with a `--no-mobsf` flag, **Then** only Appium and the main UI are started
2. **Given** the user wants to skip Appium, **When** they run the script with a `--no-appium` flag, **Then** only MobSF and the main UI are started
3. **Given** the user wants to run only the UI, **When** they run the script with `--ui-only` flag, **Then** only the main UI application starts

---

### Edge Cases

- What happens when port 8000 (MobSF) is already in use by another application?
- What happens when port 4723 (Appium) is already in use?
- How does the system handle if Python is not available to run the main UI?
- What happens if Docker is installed but the Docker daemon is not running?
- How does the script behave if the MobSF Docker image needs to be pulled (first-time run)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Script MUST check if Docker is installed and accessible before attempting to start MobSF
- **FR-002**: Script MUST check if npm/npx is installed before attempting to start Appium
- **FR-003**: Script MUST display a clear, user-friendly warning message when a dependency is not installed
- **FR-004**: Script MUST continue execution and start remaining components even if one dependency is missing
- **FR-005**: Script MUST start MobSF using the Docker command: `docker run -it --rm -p 8000:8000 opensecurity/mobile-security-framework-mobsf`
- **FR-006**: Script MUST start Appium using: `npx appium --address 127.0.0.1 --port 4723 --relaxed-security`
- **FR-007**: Script MUST start the main UI application using: `python run_ui.py`
- **FR-008**: Script MUST handle graceful shutdown when interrupted (Ctrl+C), terminating all child processes
- **FR-009**: Script MUST work on Windows operating system (PowerShell environment)
- **FR-010**: Script SHOULD support optional command-line flags to skip specific components (--no-mobsf, --no-appium, --ui-only)
- **FR-011**: Script MUST wait for MobSF and Appium to be ready before starting the main UI (reasonable delay or health check)
- **FR-012**: Script SHOULD detect if MobSF or Appium ports are already in use and warn accordingly

### Assumptions

- The user has Python installed and configured in their PATH (required to run the main application)
- The working directory when running the script is the project root (`e:\VS-projects\mobile-crawler`)
- The MobSF Docker image may need to be pulled on first run (script should allow this)
- Appium is installed globally or available via npx (no local installation required)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can start the complete application stack with a single command instead of 3+ manual commands
- **SC-002**: New users receive clear feedback within 5 seconds if any dependency is missing
- **SC-003**: All processes can be cleanly terminated with a single Ctrl+C action
- **SC-004**: 100% of startup attempts on properly configured systems result in a working application state
- **SC-005**: Script execution adds no more than 10 seconds overhead compared to manual startup (excluding initial Docker image pull)
