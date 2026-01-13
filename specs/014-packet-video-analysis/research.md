# Research: Packet Capture, Video Recording, and Security Analysis Integration

**Feature**: 014-packet-video-analysis  
**Date**: 2025-01-27  
**Status**: Complete

## Research Tasks

### 1. PCAPdroid Integration Pattern

**Task**: Research PCAPdroid API integration for Android network traffic capture

**Findings**:
- PCAPdroid provides an Activity-based API via ADB intents
- Standard activity: `com.emanuelef.remote_capture/.activities.CaptureCtrl`
- Control via `am start` commands with intent extras:
  - `action=start` with `pcap_name`, `app_filter`, `pcap_dump_mode`
  - `action=stop` to stop capture
  - `action=get_status` for status queries
- PCAP files saved to `/sdcard/Download/PCAPdroid/` by default
- Optional API key for automated consent (recommended)
- TLS decryption requires root or VPN mode

**Decision**: Use async ADB command execution pattern from reference project
- Async wrapper for subprocess calls to avoid blocking
- Error detection via return codes and stderr parsing
- Automatic cleanup of device PCAP files after pull
- Configurable wait times for initialization and finalization

**Rationale**: Reference project implementation is proven and handles edge cases well. Async pattern prevents blocking crawl execution.

**Alternatives Considered**:
- Synchronous ADB calls: Rejected - blocks crawl loop
- Direct file system monitoring: Rejected - unreliable, requires polling
- PCAPdroid broadcast receiver: Rejected - more complex, requires app modification

### 2. Appium Video Recording Integration

**Task**: Research Appium video recording capabilities and best practices

**Findings**:
- Appium provides `start_recording_screen()` and `stop_recording_screen()` methods
- Video returned as base64-encoded string
- Must decode and save to file system
- Recording is device-dependent (not all devices support it)
- Video format is typically MP4
- Recording can be memory-intensive for long sessions

**Decision**: Use Appium driver's built-in recording methods
- Start recording at crawl start
- Stop and save at crawl completion
- Handle failures gracefully (device may not support recording)
- Save to session directory with descriptive filename

**Rationale**: Appium's built-in method is simplest and most reliable. No additional dependencies needed.

**Alternatives Considered**:
- ADB screenrecord: Rejected - requires separate process management
- Third-party screen recording libraries: Rejected - unnecessary complexity
- FFmpeg-based recording: Rejected - overkill, Appium handles encoding

### 3. MobSF API Integration Pattern

**Task**: Research MobSF REST API for static analysis workflow

**Findings**:
- MobSF provides REST API at `/api/v1/` endpoint
- Authentication via API key in Authorization header
- Workflow: Upload APK → Scan → Get Reports → Download PDF/JSON
- Scan is asynchronous - must poll for completion
- Reports available as PDF and JSON formats
- Security scorecard available via `/scorecard` endpoint

**Decision**: Use requests library for HTTP API calls
- Implement retry logic with exponential backoff
- Poll scan status with configurable timeout (max 5 minutes)
- Save reports to session directory
- Extract APK from device using ADB `pm path` and `adb pull`

**Rationale**: Standard HTTP client approach is straightforward. Reference project implementation provides good error handling patterns.

**Alternatives Considered**:
- MobSF Python SDK: Rejected - not officially maintained, direct API is simpler
- WebSocket for real-time updates: Rejected - adds complexity, polling is sufficient
- Synchronous blocking wait: Rejected - poor UX, need progress updates

### 4. Configuration Management Pattern

**Task**: Research how to integrate feature configuration into existing config system

**Findings**:
- Project uses `ConfigManager` with user config store (SQLite)
- Configuration keys follow UPPER_SNAKE_CASE convention
- CLI flags override config values
- UI settings persist to user config store
- Path templates support `{session_dir}` placeholder

**Decision**: Add feature configuration keys to config system
- `ENABLE_TRAFFIC_CAPTURE` (bool)
- `ENABLE_VIDEO_RECORDING` (bool)
- `ENABLE_MOBSF_ANALYSIS` (bool)
- `PCAPDROID_PACKAGE` (string, default: `com.emanuelef.remote_capture`)
- `PCAPDROID_ACTIVITY` (string, optional - auto-constructed)
- `PCAPDROID_API_KEY` (string, optional)
- `TRAFFIC_CAPTURE_OUTPUT_DIR` (path template)
- `MOBSF_API_URL` (string)
- `MOBSF_API_KEY` (string)

**Note**: Video recording output directory is not configurable - videos are automatically saved to the session directory via SessionFolderManager.

**Rationale**: Follows existing patterns. Path templates allow session-specific directories. Optional keys support graceful degradation.

**Alternatives Considered**:
- Separate config file: Rejected - breaks existing pattern
- Environment variables only: Rejected - need UI persistence
- Hardcoded defaults: Rejected - need user configurability

### 5. Error Handling and Graceful Degradation

**Task**: Research patterns for optional feature failure handling

**Findings**:
- Features should never block crawl execution
- Log errors with appropriate severity (warning for optional features)
- Return None/False for failed operations
- Continue crawl even if features fail
- Provide clear error messages for troubleshooting

**Decision**: Implement try-except blocks around all feature operations
- Log warnings (not errors) for optional feature failures
- Return None for file paths when operations fail
- Check prerequisites before attempting operations
- Validate configuration before use

**Rationale**: Features are optional enhancements. Crawl must succeed even if all features fail. User should be informed but not blocked.

**Alternatives Considered**:
- Fail fast: Rejected - violates requirement for graceful degradation
- Silent failures: Rejected - poor UX, users need feedback
- Retry all failures: Rejected - some failures are permanent (e.g., PCAPdroid not installed)

### 6. Session Directory Organization

**Task**: Research how to organize feature artifacts in session directories

**Findings**:
- Project uses `SessionFolderManager` for directory structure
- Session path stored in `runs` table
- Subfolders for different artifact types (screenshots, reports, etc.)
- Path templates resolve at runtime

**Decision**: Use subfolders within session directory
- `traffic_captures/` for PCAP files
- `video/` for video recordings
- `mobsf_scan_results/` for MobSF reports (PDF, JSON)
- Filenames include run_id, step_num, timestamp, package name

**Rationale**: Consistent with existing session organization. Easy to locate artifacts. Supports multiple files per session.

**Alternatives Considered**:
- Flat structure: Rejected - harder to organize, potential filename conflicts
- Separate root directories: Rejected - breaks session organization
- Database-only storage: Rejected - files are too large, need filesystem access

## Technology Decisions Summary

| Technology | Decision | Rationale |
|------------|----------|-----------|
| PCAPdroid Control | ADB intents via async subprocess | Proven pattern, handles edge cases |
| Video Recording | Appium built-in methods | Simplest, no extra dependencies |
| MobSF Integration | requests library + polling | Standard HTTP client, good error handling |
| Configuration | ConfigManager with new keys | Follows existing patterns |
| Error Handling | Try-except with warnings | Graceful degradation required |
| Artifact Storage | Session subdirectories | Consistent with existing structure |

## Dependencies

### External Dependencies (User-Provided)
- PCAPdroid Android app (must be installed on device)
- MobSF server (must be running and accessible)
- ADB (must be in PATH or configured)
- Sufficient device storage for videos/PCAPs

### Python Dependencies (Already in Project)
- `appium-python-client` (for video recording)
- `requests` (for MobSF API)
- Standard library: `asyncio`, `subprocess`, `base64`, `os`, `time`

## Integration Points

1. **CrawlerLoop**: Initialize managers, call start/stop at appropriate lifecycle hooks
2. **CLI crawl command**: Parse flags, pass to config, initialize managers
3. **UI settings panel**: Add checkboxes and configuration fields
4. **ConfigManager**: Add new configuration keys with defaults
5. **SessionFolderManager**: Use for artifact directory resolution

## Open Questions Resolved

- ✅ Should features be synchronous or asynchronous? → Async for ADB, sync for Appium (handled by driver)
- ✅ How to handle long-running MobSF scans? → Polling with timeout, show progress
- ✅ Where to store artifacts? → Session subdirectories
- ✅ How to handle missing dependencies? → Graceful degradation with warnings
- ✅ Should features be mandatory or optional? → Optional (per spec requirements)

## References

- PCAPdroid API Documentation: https://github.com/emanuele-f/PCAPdroid/blob/master/docs/app_api.md
- Appium Python Client: https://github.com/appium/python-client
- MobSF API Documentation: https://mobsf.github.io/docs/#/apis
- Reference Project: `old-project-for-refrence/domain/traffic_capture_manager.py`, `video_recording_manager.py`, `infrastructure/mobsf_manager.py`
