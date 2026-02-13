# Data Model: Packet Capture, Video Recording, and Security Analysis Integration

**Feature**: 014-packet-video-analysis  
**Date**: 2025-01-27

## Overview

This feature extends the existing data model with configuration entities and session metadata for three optional features: PCAPDroid traffic capture, Appium video recording, and MobSF static analysis. The primary data entities are configuration settings (stored in config system) and file artifacts (stored in filesystem). Minimal database schema changes are needed as MobSF fields already exist in the `runs` table.

## Entities

### TrafficCaptureConfig

**Purpose**: Configuration settings for PCAPDroid traffic capture

**Attributes**:
- `enabled: bool` - Whether traffic capture is enabled
- `pcapdroid_package: str` - PCAPdroid app package name (default: `com.emanuelef.remote_capture`)
- `pcapdroid_activity: Optional[str]` - PCAPdroid activity name (auto-constructed if not provided)
- `pcapdroid_api_key: Optional[str]` - API key for automated consent (optional)
- `tls_decryption: bool` - Whether to enable TLS decryption (requires root/VPN)
- `output_dir: str` - Output directory path template (resolves at runtime)
- `device_pcap_dir: str` - Device directory where PCAP files are stored (default: `/sdcard/Download/PCAPdroid`)
- `init_wait: float` - Wait time after starting capture (seconds, default: 3.0)
- `finalize_wait: float` - Wait time after stopping capture before pull (seconds, default: 2.0)

**Storage**: Configuration system (ConfigManager, user_config_store)

**Relationships**: 
- Referenced by `TrafficCaptureManager` instance
- Used during crawl session lifecycle

**Validation Rules**:
- `pcapdroid_package` must be non-empty if enabled
- `output_dir` must be a valid path template
- `init_wait` and `finalize_wait` must be >= 0

### VideoRecordingConfig

**Purpose**: Configuration settings for Appium video recording

**Attributes**:
- `enabled: bool` - Whether video recording is enabled
- `filename_template: Optional[str]` - Filename template with placeholders (optional, has default)

**Storage**: Configuration system (ConfigManager, user_config_store)

**Relationships**:
- Referenced by `VideoRecordingManager` instance
- Used during crawl session lifecycle
- Videos are automatically saved to session directory (no configurable output directory)

**Validation Rules**:
- `filename_template` placeholders: `{run_id}`, `{step_num}`, `{timestamp}`, `{package}`

### MobSFConfig

**Purpose**: Configuration settings for MobSF static analysis

**Attributes**:
- `enabled: bool` - Whether MobSF analysis is enabled
- `api_url: str` - MobSF API base URL (e.g., `http://localhost:8000/api/v1`)
- `api_key: str` - MobSF API key for authentication
- `scan_timeout: int` - Maximum time to wait for scan completion (seconds, default: 300)
- `poll_interval: int` - Interval between status polls (seconds, default: 2)
- `output_dir: str` - Output directory path template for reports (resolves at runtime)

**Storage**: Configuration system (ConfigManager, user_config_store)

**Relationships**:
- Referenced by `MobSFManager` instance
- Used after crawl completion

**Validation Rules**:
- `api_url` must be a valid HTTP/HTTPS URL
- `api_key` must be non-empty if enabled
- `scan_timeout` must be > 0
- `poll_interval` must be > 0

### TrafficCaptureSession

**Purpose**: Runtime state for an active traffic capture session

**Attributes**:
- `is_capturing: bool` - Whether capture is currently active
- `pcap_filename_on_device: Optional[str]` - Filename on device (set when starting)
- `local_pcap_file_path: Optional[str]` - Local file path (set when starting)
- `run_id: Optional[int]` - Associated run ID
- `step_num: Optional[int]` - Associated step number
- `start_time: Optional[datetime]` - When capture started
- `stop_time: Optional[datetime]` - When capture stopped

**Storage**: In-memory (manager instance state)

**Relationships**:
- Associated with a `Run` (via run_id)
- Managed by `TrafficCaptureManager` instance

**State Transitions**:
- `idle` → `capturing` (on `start_capture()`)
- `capturing` → `idle` (on `stop_capture_and_pull()`)
- `capturing` → `error` (on failure, then back to `idle`)

### VideoRecordingSession

**Purpose**: Runtime state for an active video recording session

**Attributes**:
- `is_recording: bool` - Whether recording is currently active
- `video_file_path: Optional[str]` - Local file path (set when starting)
- `run_id: Optional[int]` - Associated run ID
- `step_num: Optional[int]` - Associated step number
- `start_time: Optional[datetime]` - When recording started
- `stop_time: Optional[datetime]` - When recording stopped

**Storage**: In-memory (manager instance state)

**Relationships**:
- Associated with a `Run` (via run_id)
- Managed by `VideoRecordingManager` instance

**State Transitions**:
- `idle` → `recording` (on `start_recording()`)
- `recording` → `idle` (on `stop_recording_and_save()`)
- `recording` → `error` (on failure, then back to `idle`)

### MobSFAnalysisSession

**Purpose**: Runtime state for a MobSF analysis session

**Attributes**:
- `package_name: str` - Package name being analyzed
- `apk_path: Optional[str]` - Local path to extracted APK
- `file_hash: Optional[str]` - MobSF file hash (from upload)
- `scan_id: Optional[str]` - MobSF scan ID
- `status: str` - Analysis status (`pending`, `scanning`, `completed`, `error`)
- `pdf_report_path: Optional[str]` - Path to PDF report
- `json_report_path: Optional[str]` - Path to JSON report
- `security_score: Optional[float]` - Security score from MobSF
- `start_time: Optional[datetime]` - When analysis started
- `end_time: Optional[datetime]` - When analysis completed

**Storage**: 
- In-memory (manager instance state)
- Database: `runs` table has fields: `mobsf_security_score`, `mobsf_high_issues`, `mobsf_medium_issues`, `mobsf_low_issues`

**Relationships**:
- Associated with a `Run` (via package_name/run_id)
- Managed by `MobSFManager` instance

**State Transitions**:
- `idle` → `extracting` (on APK extraction)
- `extracting` → `uploading` (on upload start)
- `uploading` → `scanning` (on scan start)
- `scanning` → `completed` (on scan completion)
- Any state → `error` (on failure)

## Database Schema Changes

### Existing Schema (No Changes Needed)

The `runs` table already includes MobSF-related fields:
```sql
mobsf_security_score REAL,
mobsf_high_issues INTEGER DEFAULT 0,
mobsf_medium_issues INTEGER DEFAULT 0,
mobsf_low_issues INTEGER DEFAULT 0,
```

These fields can be populated by `MobSFManager` after analysis completes.

### Configuration Storage

Configuration is stored in the user config store (SQLite database `user_config.db`):
- Table: `user_config` (key-value pairs)
- Keys: `ENABLE_TRAFFIC_CAPTURE`, `ENABLE_VIDEO_RECORDING`, `ENABLE_MOBSF_ANALYSIS`, etc.
- Values: JSON-encoded or string values

## File Artifacts

### PCAP Files

**Location**: `{session_dir}/traffic_captures/`
**Naming**: `{package}_run{run_id}_step{step_num}_{timestamp}.pcap`
**Format**: PCAP (standard network capture format)
**Size**: Typically <10MB per session

### Video Files

**Location**: `{session_dir}/video/`
**Naming**: `{package}_run{run_id}_step{step_num}_{timestamp}.mp4`
**Format**: MP4 (H.264 encoded)
**Size**: Variable, can be 100MB+ for long sessions

### MobSF Reports

**Location**: `{session_dir}/mobsf_scan_results/`
**Files**:
- `{file_hash}_report.pdf` - PDF security report
- `{file_hash}_report.json` - JSON detailed analysis
**Format**: PDF and JSON
**Size**: PDF typically 1-5MB, JSON typically 100KB-1MB

## Data Flow

### Traffic Capture Flow

1. User enables via CLI flag or UI setting → Config updated
2. Crawl starts → `TrafficCaptureManager` initialized with config
3. `start_capture_async()` called → ADB intent sent, filename set
4. Crawl runs → PCAPdroid captures traffic
5. Crawl completes → `stop_capture_and_pull_async()` called → PCAP file pulled and saved
6. File path returned → Stored in session directory

### Video Recording Flow

1. User enables via CLI flag or UI setting → Config updated
2. Crawl starts → `VideoRecordingManager` initialized with config
3. `start_recording()` called → Appium recording started
4. Crawl runs → Video recorded by Appium
5. Crawl completes → `stop_recording_and_save()` called → Video decoded and saved
6. File path returned → Stored in session directory

### MobSF Analysis Flow

1. User enables via CLI flag or UI setting → Config updated
2. Crawl completes → `MobSFManager` extracts APK from device
3. APK uploaded to MobSF → Scan ID received
4. Poll scan status → Wait for completion
5. Reports downloaded → PDF and JSON saved to session directory
6. Security score extracted → Stored in `runs` table

## Validation Rules

### Configuration Validation

- All URL fields must be valid HTTP/HTTPS URLs
- All path templates must resolve to valid directories
- Boolean flags must be true/false
- Numeric fields must be positive
- API keys must be non-empty strings if feature is enabled

### Runtime Validation

- PCAPdroid must be installed before starting capture
- Device must support video recording before starting recording
- MobSF server must be reachable before starting analysis
- Sufficient storage must be available for artifacts
- ADB must be accessible for PCAPdroid and APK extraction

## Relationships Summary

```
Run (1) ──< (0..1) TrafficCaptureSession
Run (1) ──< (0..1) VideoRecordingSession  
Run (1) ──< (0..1) MobSFAnalysisSession

TrafficCaptureConfig ──> TrafficCaptureManager ──> TrafficCaptureSession
VideoRecordingConfig ──> VideoRecordingManager ──> VideoRecordingSession
MobSFConfig ──> MobSFManager ──> MobSFAnalysisSession
```

## Notes

- All session entities are ephemeral (in-memory only)
- Configuration persists across sessions
- File artifacts persist in filesystem
- Database only stores MobSF results (security scores, issue counts)
- No foreign key constraints needed (sessions are runtime-only)
