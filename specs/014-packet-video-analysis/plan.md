# Implementation Plan: Packet Capture, Video Recording, and Security Analysis Integration

**Branch**: `014-packet-video-analysis` | **Date**: 2025-01-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-packet-video-analysis/spec.md`

## Summary

Integrate three complementary features from the reference project into the mobile crawler: PCAPDroid packet capture for network traffic analysis, Appium-based video recording for session documentation, and MobSF static analysis for security assessment. All three features must be integrated into both CLI and UI interfaces with automatic lifecycle management during crawl sessions. The implementation will enhance existing stub implementations and add proper integration points in the crawler loop, CLI commands, and UI components.

## Technical Context

**Language/Version**: Python 3.9+ (project requires Python 3.9+)  
**Primary Dependencies**: 
- `appium-python-client>=3.0.0` (for video recording via Appium driver)
- `requests>=2.31.0` (for MobSF API integration)
- `PySide6>=6.6.0` (for UI components)
- ADB (Android Debug Bridge) for PCAPdroid control and APK extraction
- PCAPdroid Android app (must be installed on device)
- MobSF server (must be running for static analysis)

**Storage**: 
- Filesystem: PCAP files, video files (MP4), MobSF reports (PDF, JSON) stored in session directories
- SQLite database: Optional metadata storage for analysis results (already has MobSF fields in runs table)

**Testing**: 
- `pytest>=7.0.0` with `pytest-qt>=4.0.0` for UI tests
- Unit tests for manager classes
- Integration tests for CLI commands and UI workflows
- Mock ADB commands and MobSF API responses for testing

**Target Platform**: 
- Development: Windows/Linux/macOS (where ADB and Python run)
- Target: Android devices/emulators (where PCAPdroid and apps run)
- MobSF server: Can run locally or remotely

**Project Type**: Single project (Python application with CLI and GUI interfaces)

**Performance Goals**: 
- Feature initialization should not delay crawl start by more than 2 seconds
- MobSF analysis should complete within 5 minutes for typical APK sizes (<50MB)
- Video recording should not impact crawl performance (Appium handles this asynchronously)
- PCAP capture overhead should be minimal (<100ms per operation)

**Constraints**: 
- Features must fail gracefully without stopping crawl if dependencies unavailable
- All operations must be non-blocking or have timeouts
- Storage requirements: Videos can be large (100MB+ per session), PCAP files typically smaller (<10MB)
- Network dependency: MobSF requires network connectivity to API server
- Device dependency: PCAPdroid must be installed, video recording requires device support

**Scale/Scope**: 
- Single crawl session at a time (current architecture)
- Multiple features can run simultaneously (traffic capture + video + MobSF)
- Session artifacts organized in directory structure per run
- Configuration persisted across sessions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Note**: Constitution file appears to be a template. Assuming standard Python project practices:
- Test-first development (TDD) where applicable
- Integration tests for cross-component features
- Simplicity: Reuse existing patterns from reference project
- Error handling: Graceful degradation when features unavailable

**Gates**:
- ✅ Single project structure (no new projects needed)
- ✅ Existing infrastructure patterns can be extended
- ✅ No new external services beyond MobSF (already referenced in codebase)
- ✅ Features are optional (graceful degradation supported)

## Project Structure

### Documentation (this feature)

```text
specs/014-packet-video-analysis/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/mobile_crawler/
├── domain/
│   ├── traffic_capture_manager.py    # UPDATE: Enhance existing stub with reference implementation
│   ├── video_recording_manager.py    # UPDATE: Enhance existing stub with reference implementation
│   └── [existing domain modules]
├── infrastructure/
│   ├── mobsf_manager.py              # UPDATE: Enhance existing implementation with reference features
│   ├── adb_client.py                 # NEW: ADB command wrapper (if not exists)
│   └── [existing infrastructure modules]
├── core/
│   ├── crawler_loop.py               # UPDATE: Add feature manager initialization and lifecycle hooks
│   └── [existing core modules]
├── cli/
│   ├── commands/
│   │   ├── crawl.py                  # UPDATE: Add --enable-traffic-capture, --enable-video-recording, --enable-mobsf-analysis flags
│   │   └── [existing CLI commands]
│   └── [existing CLI modules]
├── ui/
│   ├── widgets/
│   │   ├── settings_panel.py         # UPDATE: Add feature configuration UI
│   │   ├── mobsf_widget.py           # NEW: MobSF connection test and status widget
│   │   └── [existing UI widgets]
│   └── [existing UI modules]
└── config/
    ├── config_manager.py              # UPDATE: Add feature configuration keys
    └── [existing config modules]

tests/
├── domain/
│   ├── test_traffic_capture_manager.py    # NEW: Unit tests
│   ├── test_video_recording_manager.py    # NEW: Unit tests
│   └── [existing domain tests]
├── infrastructure/
│   ├── test_mobsf_manager.py             # UPDATE: Enhance existing tests
│   └── [existing infrastructure tests]
├── integration/
│   ├── test_feature_integration.py       # NEW: Integration tests for CLI/UI
│   └── [existing integration tests]
└── [existing test modules]
```

**Structure Decision**: Single project structure as per project standard. Features are integrated as:
- Domain managers (`traffic_capture_manager.py`, `video_recording_manager.py`) for business logic
- Infrastructure manager (`mobsf_manager.py`) for external service integration
- Core integration (`crawler_loop.py`) for lifecycle management
- CLI/UI integration for user-facing controls
- Configuration system for settings persistence

## Complexity Tracking

No constitution violations to justify. This feature:
- Extends existing patterns (managers, CLI commands, UI widgets)
- Reuses reference project code structure
- Adds optional features with graceful degradation
- Follows established project architecture
