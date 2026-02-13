# Quickstart: Statistics Display and Crawl Stability

**Feature**: 025-stats-and-stability  
**Date**: 2026-01-16

## Overview

This feature adds real-time operation timing metrics to the Statistics panel and fixes several crawl stability issues.

## What's New

### 1. Extended Statistics Panel

The Statistics tab now shows additional timing metrics:

```
┌─ Statistics ─────────────────────────┐
│                                      │
│ Crawl Progress                       │
│ Total Steps: 5    Actions OK: 12     │
│ Actions Failed: 0                    │
│ Step Progress: [████████░░] 5/15     │
│                                      │
│ Screen Discovery                     │
│ Unique Screens: 4  Total Visits: 6   │
│ Screens/min: 2.4                     │
│                                      │
│ AI Performance                       │
│ AI Calls: 5       Avg Response: 3.2s │
│                                      │
│ ★ Operation Timing (NEW)             │
│ OCR Avg: 5771ms   Action Avg: 234ms  │
│ Screenshot Avg: 156ms                │
│                                      │
│ Duration                             │
│ Elapsed: 120s                        │
│ Time Progress: [████░░░] 120/300s    │
└──────────────────────────────────────┘
```

### 2. Improved Crawl Duration Enforcement

- Crawls now reliably run for the configured duration limit
- Clear completion reasons are logged
- Fixed early termination issues

### 3. PCAPdroid Integration Improvements

- Better pre-flight validation
- Clear error messages when API key configuration is incorrect
- Guidance on proper PCAPdroid setup

### 4. Video Recording Robustness

- Graceful handling of stale recording processes
- No longer crashes when cleaning up non-existent processes
- Crawl continues even if video recording fails

## Quick Verification

### Verify Timing Statistics

1. Start the mobile crawler: `python run_ui.py`
2. Configure a crawl with any app
3. Start the crawl
4. Observe the Statistics panel - you should see:
   - OCR Avg updating after each step
   - Action Avg updating after each action
   - Screenshot Avg updating after each screenshot

### Verify Duration Limit

1. Set crawl duration to 60 seconds in Settings
2. Start a crawl on an app with multiple screens
3. Observe the crawl runs for approximately 60 seconds
4. Check the completion log shows "Duration limit reached"

### Verify PCAPdroid

1. Ensure PCAPdroid is installed on device
2. Open PCAPdroid app on device → Settings → API Control
3. Enable API Control and note the API key
4. Enter the same key in mobile-crawler Settings → PCAPdroid API Key
5. Enable traffic capture and start crawl
6. No permission dialog should appear on device

### Verify Video Recording

1. Enable video recording in Settings
2. Start a crawl
3. Check console logs - no "No such process" errors
4. After crawl, check session folder for video file

## Troubleshooting

### "OCR Avg: 0ms" despite OCR running

- Ensure grounding is enabled (it's on by default)
- Check logs for OCR errors

### Crawl still stopping early

- Check completion reason in logs
- Look for step failures or "signup_completed" signals
- Verify max_crawl_steps setting isn't too low

### PCAPdroid permission dialog still appears

- Verify API key in mobile-crawler matches PCAPdroid app exactly
- Ensure PCAPdroid API Control is enabled
- Try restarting PCAPdroid app

### Video recording fails

- Check device supports screen recording
- Verify Appium relaxed-security mode is enabled
- Try manually: `adb shell screenrecord /sdcard/test.mp4`

## Code Changes Summary

| File | Change |
|------|--------|
| `ui/main_window.py` | Extended CrawlStatistics dataclass |
| `ui/widgets/stats_dashboard.py` | Added Operation Timing section |
| `ui/signal_adapter.py` | Added timing signals |
| `core/crawler_event_listener.py` | Added timing event methods |
| `core/crawler_loop.py` | Emit timing events, improved logging |
| `domain/traffic_capture_manager.py` | Better pre-flight validation |
| `domain/video_recording_manager.py` | Graceful error handling |
| `infrastructure/appium_driver.py` | Handle stale process cleanup |
