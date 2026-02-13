# Feature Specification: Packet Capture, Video Recording, and Security Analysis Integration

**Feature Branch**: `014-packet-video-analysis`  
**Created**: 2025-01-27  
**Status**: Draft  
**Input**: User description: "E:\VS-projects\mobile-crawler\old-project-for-refrence use the refrence project to get the code for intergrating the PCAPDroid packet capture, MOBSf for static analysis and report generation, video capture of the crawl session with appium so we can implement these features here and integrate them in cli and ui"

## Clarifications

### Session 2025-01-27

- Q: Where should MobSF scan progress updates be displayed to users? → A: Both CLI and UI (with appropriate format for each)
- Q: If a feature is enabled in both CLI flag and UI settings, which takes precedence? → A: CLI flags override UI settings (CLI highest precedence)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enable Network Traffic Capture During Crawl (Priority: P1)

Security researchers and testers need to capture network traffic during mobile app crawling sessions to analyze API calls, data transmission, and potential security vulnerabilities. Users should be able to enable PCAPDroid packet capture via CLI or UI, and the system should automatically start capturing when a crawl begins and save the PCAP file when the crawl completes.

**Why this priority**: Network traffic analysis is a core security testing capability that provides immediate value for understanding app behavior and identifying potential vulnerabilities. This is the most commonly used feature among the three.

**Independent Test**: Can be fully tested by starting a crawl with `--enable-traffic-capture` flag, verifying PCAP file is created in the session directory, and confirming the file contains network traffic data. Delivers immediate value for security analysis.

**Acceptance Scenarios**:

1. **Given** a user has PCAPdroid installed on their Android device and configured in the system, **When** they start a crawl with traffic capture enabled via CLI flag `--enable-traffic-capture`, **Then** the system automatically starts PCAPdroid capture at crawl start and saves a PCAP file to the session directory when the crawl completes
2. **Given** a user has traffic capture enabled in UI settings, **When** they start a crawl session from the UI, **Then** the system captures network traffic and displays the saved PCAP file path in the session artifacts
3. **Given** traffic capture is enabled but PCAPdroid is not installed or accessible, **When** the system attempts to start capture, **Then** the system logs a clear error message and continues the crawl without capture (graceful degradation)

---

### User Story 2 - Record Video of Crawl Session (Priority: P1)

Users need to record video of the entire crawl session to review app interactions, debug issues, and create documentation. Users should be able to enable video recording via CLI or UI, and the system should automatically start recording when a crawl begins and save the video file when the crawl completes.

**Why this priority**: Video recording provides visual documentation of crawl sessions, which is essential for debugging, analysis, and reporting. This feature has similar priority to traffic capture as both are commonly used together.

**Independent Test**: Can be fully tested by starting a crawl with `--enable-video-recording` flag, verifying MP4 file is created in the session directory, and confirming the video contains the crawl session footage. Delivers immediate value for session review and documentation.

**Acceptance Scenarios**:

1. **Given** a user starts a crawl with video recording enabled via CLI flag `--enable-video-recording`, **When** the crawl session runs, **Then** the system automatically starts video recording at crawl start and saves an MP4 file to the session directory when the crawl completes
2. **Given** a user has video recording enabled in UI settings, **When** they start a crawl session from the UI, **Then** the system records the session and displays the saved video file path in the session artifacts
3. **Given** video recording fails to start (e.g., device doesn't support it), **When** the system attempts to start recording, **Then** the system logs a clear error message and continues the crawl without recording (graceful degradation)

---

### User Story 3 - Perform Static Security Analysis with MobSF (Priority: P2)

Security researchers need to perform static analysis of Android apps to identify security vulnerabilities, code issues, and compliance problems. Users should be able to enable MobSF analysis via CLI or UI, and the system should automatically extract the APK, upload it to MobSF, run the scan, and generate PDF and JSON reports when the crawl completes.

**Why this priority**: Static analysis provides comprehensive security insights but requires a MobSF server setup, making it less immediately accessible than traffic capture or video recording. It's valuable but has dependencies that may not always be available.

**Independent Test**: Can be fully tested by starting a crawl with `--enable-mobsf-analysis` flag (with MobSF server running), verifying APK is extracted, scan completes, and PDF/JSON reports are saved to the session directory. Delivers value for comprehensive security assessment.

**Acceptance Scenarios**:

1. **Given** a user has MobSF server running and configured with API key, **When** they start a crawl with `--enable-mobsf-analysis` flag, **Then** the system automatically extracts the APK after crawl completion, uploads it to MobSF, runs static analysis with progress updates visible in CLI output/logs, and saves PDF and JSON reports to the session directory
2. **Given** a user has MobSF analysis enabled in UI settings, **When** they start a crawl session from the UI, **Then** the system performs the analysis after crawl completion with progress updates visible in UI progress widget/status bar, and displays report paths in the session artifacts
3. **Given** MobSF analysis is enabled but the server is unreachable or API key is invalid, **When** the system attempts to perform analysis, **Then** the system logs a clear error message with troubleshooting guidance and continues without analysis (graceful degradation)

---

### User Story 4 - Configure Features via Settings (Priority: P2)

Users need to configure feature settings (API keys, output directories, server URLs) through both CLI configuration files and UI settings panels. Settings should persist across sessions and be validated before use.

**Why this priority**: Configuration is essential for feature usability but is a supporting capability rather than the core feature. Users need to set up once and reuse settings.

**Independent Test**: Can be fully tested by setting configuration values via CLI config or UI, starting a crawl, and verifying the features use the configured settings. Delivers value for user convenience and feature customization.

**Acceptance Scenarios**:

1. **Given** a user configures MobSF API URL and API key in UI settings, **When** they save the settings, **Then** the configuration is persisted and used for subsequent MobSF analysis operations
2. **Given** a user sets traffic capture output directory via CLI config, **When** they start a crawl with traffic capture enabled, **Then** PCAP files are saved to the configured directory
3. **Given** a user provides invalid configuration (e.g., malformed URL), **When** they attempt to save settings, **Then** the system validates the configuration and displays clear error messages indicating what needs to be corrected
4. **Given** video recording is enabled, **When** a crawl completes, **Then** video files are automatically saved to the session directory (no configuration needed)

---

### Edge Cases

- What happens when multiple crawl sessions run simultaneously with the same feature enabled? (Each session should have isolated artifacts)
- How does system handle device storage full during video recording or PCAP capture? (System should detect and log error, attempt cleanup, continue gracefully)
- What happens when PCAPdroid capture is started but the app crashes or becomes unresponsive? (System should detect failure, log error, and continue crawl)
- How does system handle MobSF scan timeout or very long scan duration? (System should have configurable timeout, log progress, and handle timeout gracefully)
- What happens when video recording file becomes too large for available storage? (System should detect storage issues early and log warnings)
- How does system handle network interruption during MobSF API calls? (System should retry with exponential backoff, log errors, and fail gracefully)
- What happens when PCAPdroid requires user consent on device during capture? (System should log instructions for user, wait for consent, or handle timeout)
- How does system handle Appium video recording not supported on certain devices? (System should detect capability, log clear message, and continue without recording)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to enable/disable PCAPDroid packet capture via CLI flag `--enable-traffic-capture` or UI checkbox setting (CLI flags take precedence over UI settings when both are provided)
- **FR-002**: System MUST automatically start PCAPDroid capture when a crawl session begins if traffic capture is enabled
- **FR-003**: System MUST automatically stop PCAPDroid capture and pull the PCAP file to the local session directory when a crawl session completes
- **FR-004**: System MUST save PCAP files with descriptive names including app package, run ID, step number, and timestamp
- **FR-005**: System MUST allow users to configure PCAPDroid package name, activity, API key, and output directory via configuration
- **FR-006**: System MUST allow users to enable/disable video recording via CLI flag `--enable-video-recording` or UI checkbox setting (CLI flags take precedence over UI settings when both are provided)
- **FR-007**: System MUST automatically start video recording when a crawl session begins if video recording is enabled
- **FR-008**: System MUST automatically stop video recording and save the video file to the local session directory when a crawl session completes
- **FR-009**: System MUST save video files in MP4 format with descriptive names including app package, run ID, step number, and timestamp
- **FR-010**: System MUST allow users to enable/disable MobSF static analysis via CLI flag `--enable-mobsf-analysis` or UI checkbox setting (CLI flags take precedence over UI settings when both are provided)
- **FR-011**: System MUST automatically extract the APK from the device after crawl completion if MobSF analysis is enabled
- **FR-012**: System MUST upload the extracted APK to MobSF server and initiate static analysis scan
- **FR-013**: System MUST monitor MobSF scan progress and display status updates to users
- **FR-014**: System MUST download and save PDF and JSON reports from MobSF to the session directory when scan completes
- **FR-015**: System MUST allow users to configure MobSF API URL and API key via configuration
- **FR-016**: System MUST validate MobSF server connectivity and API key before attempting analysis
- **FR-017**: System MUST handle feature failures gracefully without stopping the crawl session (features should be optional)
- **FR-018**: System MUST log all feature operations (start, stop, errors) with appropriate log levels
- **FR-019**: System MUST organize all feature artifacts (PCAP files, videos, MobSF reports) in the session directory structure
- **FR-020**: System MUST provide UI controls for testing MobSF connection and viewing feature status
- **FR-021**: System MUST allow users to configure feature-specific settings (e.g., PCAPDroid TLS decryption, MobSF scan options) via configuration

### Key Entities *(include if feature involves data)*

- **Traffic Capture Session**: Represents a network capture session, includes device filename, local file path, capture status, and metadata (run ID, step number, timestamp)
- **Video Recording Session**: Represents a video recording session, includes video file path, recording status, and metadata (run ID, step number, timestamp)
- **MobSF Analysis Session**: Represents a MobSF static analysis session, includes APK path, file hash, scan status, report paths (PDF, JSON), and security score
- **Feature Configuration**: Represents user-configured settings for all three features, includes enable/disable flags, API keys, server URLs, output directories, and feature-specific options

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can enable traffic capture, video recording, or MobSF analysis in under 30 seconds via CLI flags or UI settings
- **SC-002**: System successfully captures network traffic for 95% of crawl sessions when traffic capture is enabled and PCAPdroid is properly configured
- **SC-003**: System successfully records video for 95% of crawl sessions when video recording is enabled and device supports it
- **SC-004**: System successfully completes MobSF analysis for 90% of crawl sessions when MobSF analysis is enabled and server is accessible
- **SC-005**: Feature failures (capture/recording/analysis errors) do not interrupt crawl sessions - crawl completes successfully even if features fail
- **SC-006**: All feature artifacts (PCAP files, videos, reports) are saved to correct session directories with descriptive filenames in 100% of successful operations
- **SC-007**: Users receive clear error messages and troubleshooting guidance when features fail, enabling them to resolve issues independently in 80% of cases
- **SC-008**: MobSF scan progress is visible to users with status updates at least every 10 seconds during analysis (displayed in CLI output/logs for CLI users, and in UI progress widget/status bar for UI users)
- **SC-009**: Feature configuration persists correctly across sessions - users do not need to reconfigure settings for 100% of subsequent sessions
- **SC-010**: System validates feature prerequisites (PCAPdroid installed, MobSF server accessible, device video support) and provides clear feedback before crawl start

## Assumptions

- PCAPdroid app is installed on the Android device and accessible via ADB commands
- MobSF server is running and accessible at the configured API URL (when MobSF analysis is enabled)
- Android device supports Appium video recording capabilities (when video recording is enabled)
- Users have sufficient device storage for PCAP files and video recordings
- Network connectivity is available for MobSF API calls (when MobSF analysis is enabled)
- ADB is properly configured and device is connected when features are enabled
- Feature managers can be instantiated independently and operate asynchronously without blocking crawl execution
- Session directory structure is already established before features are initialized
- Configuration system supports feature flags and path templates that resolve at runtime
