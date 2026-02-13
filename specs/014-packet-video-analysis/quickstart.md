# Quickstart: Packet Capture, Video Recording, and Security Analysis Integration

**Feature**: 014-packet-video-analysis  
**Date**: 2025-01-27

## Overview

This guide provides step-by-step instructions for integrating and using the three optional features: PCAPDroid traffic capture, Appium video recording, and MobSF static analysis.

## Prerequisites

### PCAPdroid Traffic Capture
- PCAPdroid app installed on Android device
- ADB accessible (in PATH or configured)
- Device connected and authorized

### Video Recording
- Android device that supports Appium video recording
- Appium driver connected to device

### MobSF Static Analysis
- MobSF server running and accessible
- MobSF API key configured
- Network connectivity to MobSF server

## Configuration

### CLI Configuration

Add to your configuration file or environment variables:

```bash
# Enable features
ENABLE_TRAFFIC_CAPTURE=true
ENABLE_VIDEO_RECORDING=true
ENABLE_MOBSF_ANALYSIS=true

# PCAPdroid settings
PCAPDROID_PACKAGE=com.emanuelef.remote_capture
PCAPDROID_API_KEY=your_api_key_here  # Optional but recommended
TRAFFIC_CAPTURE_OUTPUT_DIR={session_dir}/traffic_captures

# Video recording settings
# Note: Videos are automatically saved to session directory, no configuration needed

# MobSF settings
MOBSF_API_URL=http://localhost:8000/api/v1
MOBSF_API_KEY=your_mobsf_api_key
```

### UI Configuration

1. Open UI settings panel
2. Navigate to "Features" section
3. Enable desired features via checkboxes
4. Configure API URLs and keys
5. Save settings

## Usage

### CLI Usage

#### Enable Traffic Capture

```bash
mobile-crawler-cli crawl \
  --device emulator-5554 \
  --package com.example.app \
  --model gemini-pro \
  --enable-traffic-capture
```

#### Enable Video Recording

```bash
mobile-crawler-cli crawl \
  --device emulator-5554 \
  --package com.example.app \
  --model gemini-pro \
  --enable-video-recording
```

#### Enable MobSF Analysis

```bash
mobile-crawler-cli crawl \
  --device emulator-5554 \
  --package com.example.app \
  --model gemini-pro \
  --enable-mobsf-analysis
```

#### Enable All Features

```bash
mobile-crawler-cli crawl \
  --device emulator-5554 \
  --package com.example.app \
  --model gemini-pro \
  --enable-traffic-capture \
  --enable-video-recording \
  --enable-mobsf-analysis
```

### UI Usage

1. Start UI: `mobile-crawler-gui`
2. Configure features in settings (if not already configured)
3. Select device and app package
4. Start crawl - features will automatically start/stop based on settings
5. View artifacts in session directory after crawl completes

## Integration Steps

### Step 1: Update Domain Managers

Enhance existing stub implementations in `src/mobile_crawler/domain/`:

- `traffic_capture_manager.py` - Add async ADB command execution
- `video_recording_manager.py` - Add Appium recording methods

### Step 2: Update Infrastructure Manager

Enhance existing MobSF manager in `src/mobile_crawler/infrastructure/`:

- `mobsf_manager.py` - Add complete analysis workflow

### Step 3: Integrate into CrawlerLoop

Update `src/mobile_crawler/core/crawler_loop.py`:

```python
# Add manager parameters to __init__
def __init__(
    self,
    # ... existing parameters ...
    traffic_capture_manager: Optional[TrafficCaptureManager] = None,
    video_recording_manager: Optional[VideoRecordingManager] = None,
    mobsf_manager: Optional[MobSFManager] = None,
):
    # ... store managers ...

# Add start hooks in run() method
async def run(self, run_id: int) -> None:
    # ... existing initialization ...
    
    # Start features
    if self.traffic_capture_manager:
        await self.traffic_capture_manager.start_capture_async(run_id, step_num=1)
    if self.video_recording_manager:
        self.video_recording_manager.start_recording(run_id, step_num=1)
    
    # ... main crawl loop ...
    
    # Stop features and run analysis
    if self.traffic_capture_manager and self.traffic_capture_manager.is_capturing():
        pcap_path = await self.traffic_capture_manager.stop_capture_and_pull_async(run_id, step_number)
    if self.video_recording_manager and self.video_recording_manager.is_recording():
        video_path = self.video_recording_manager.stop_recording_and_save()
    if self.mobsf_manager:
        result = self.mobsf_manager.analyze_package(run.app_package, run.device_id, run_id)
```

### Step 4: Add CLI Flags

Update `src/mobile_crawler/cli/commands/crawl.py`:

```python
@click.option('--enable-traffic-capture', is_flag=True, help='Enable PCAPdroid traffic capture')
@click.option('--enable-video-recording', is_flag=True, help='Enable video recording')
@click.option('--enable-mobsf-analysis', is_flag=True, help='Enable MobSF static analysis')
def crawl(..., enable_traffic_capture, enable_video_recording, enable_mobsf_analysis):
    # Override config
    if enable_traffic_capture:
        config_manager.set('ENABLE_TRAFFIC_CAPTURE', True)
    # ... initialize managers based on flags ...
```

### Step 5: Add UI Controls

Update UI widgets in `src/mobile_crawler/ui/widgets/`:

- Add checkboxes for feature enable/disable
- Add configuration fields for API keys and URLs
- Add MobSF connection test button
- Display feature status during crawl

## Testing

### Unit Tests

```bash
# Test traffic capture manager
pytest tests/domain/test_traffic_capture_manager.py

# Test video recording manager
pytest tests/domain/test_video_recording_manager.py

# Test MobSF manager
pytest tests/infrastructure/test_mobsf_manager.py
```

### Integration Tests

```bash
# Test feature integration
pytest tests/integration/test_feature_integration.py
```

### Manual Testing

1. Start crawl with feature enabled
2. Verify feature starts at crawl start
3. Verify feature stops at crawl completion
4. Check session directory for artifacts
5. Verify error handling (disable feature, test with missing dependencies)

## Troubleshooting

### Traffic Capture Not Starting

- Check PCAPdroid is installed: `adb shell pm list packages | grep pcapdroid`
- Check ADB is accessible: `adb devices`
- Check configuration: `ENABLE_TRAFFIC_CAPTURE=true`, `PCAPDROID_PACKAGE` set correctly
- Check logs for ADB command errors

### Video Recording Not Working

- Check device supports recording: Appium capability `recordVideo: true`
- Check Appium driver is connected
- Check configuration: `ENABLE_VIDEO_RECORDING=true`
- Check device storage space

### MobSF Analysis Failing

- Check MobSF server is running: `curl http://localhost:8000/api/v1/`
- Check API key is correct
- Check network connectivity
- Check APK extraction: `adb shell pm path <package>`
- Check logs for API errors

## Artifact Locations

After crawl completion, artifacts are saved to:

```
{session_dir}/
├── traffic_captures/
│   └── {package}_run{run_id}_step{step_num}_{timestamp}.pcap
├── video/
│   └── {package}_run{run_id}_step{step_num}_{timestamp}.mp4
└── mobsf_scan_results/
    ├── {file_hash}_report.pdf
    └── {file_hash}_report.json
```

## Next Steps

- Review [data-model.md](./data-model.md) for entity definitions
- Review [contracts/](./contracts/) for interface specifications
- Review [research.md](./research.md) for technology decisions
- Proceed to [tasks.md](./tasks.md) for implementation tasks
