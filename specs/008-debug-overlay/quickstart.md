# Quickstart: Debug Overlay & Step-by-Step Mode

**Feature**: 008-debug-overlay  
**Date**: 2026-01-12

## Overview

This feature adds two debugging capabilities:
1. **Coordinate Overlays**: Visualize AI-predicted bounding boxes on screenshots
2. **Step-by-Step Mode**: Pause after each step to inspect before continuing

## Prerequisites

- Python 3.11+
- Existing dependencies (PySide6, Pillow) already installed
- Mobile crawler running with UI (`python run_ui.py`)

## Quick Usage

### 1. Enable Step-by-Step Mode

1. Launch the crawler UI: `python run_ui.py`
2. Find the **"Step-by-Step Mode"** checkbox in the Crawl Controls section
3. Check the box before starting a crawl
4. Click **"Start Crawl"**

### 2. Inspect Step Data

When the crawler pauses after each step:

1. View the **AI Monitor Panel** to see the latest AI interaction
2. Click **"Show Details"** on any step to see:
   - Screenshot with bounding box overlays
   - Parsed actions with coordinates
   - AI reasoning
3. The overlays show:
   - **Colored rectangles** around target areas
   - **Numbered labels** (1, 2, 3...) for action order
   - **Center dots** showing exact tap points

### 3. Advance to Next Step

- Click the **"Next Step"** button to execute the next step
- The crawler will pause again after the step completes
- To run continuously, uncheck "Step-by-Step Mode" and click "Resume"

### 4. Review Saved Screenshots

After the crawl completes:

1. Navigate to `screenshots/run_{id}/`
2. Find pairs of files:
   - `screenshot_{timestamp}.png` - Original screenshot
   - `screenshot_{timestamp}_annotated.png` - With bounding box overlays
3. Use these for post-run analysis or sharing

## Color Legend

| Color | Meaning |
|-------|---------|
| 🟢 Green | Action 1 (primary) |
| 🔵 Blue | Action 2 |
| 🟠 Orange | Action 3 |
| 🟣 Magenta | Action 4 |
| 🔵 Cyan | Action 5+ |
| 🔴 Red (dashed) | Invalid/out-of-bounds coordinates |

## Tips

- **Mid-run toggle**: You can enable/disable step-by-step mode during a running crawl. The change takes effect after the current step completes.
- **Quick exit**: Click "Stop" anytime to end the crawl gracefully.
- **Compare runs**: Annotated screenshots are saved with every run, making it easy to compare AI behavior across sessions.

## Troubleshooting

### Overlays not showing in UI
- Ensure the step has completed (not still "Pending")
- Click "Show Details" to open the full step view
- Check that AI returned actions (some steps may have no actions)

### Annotated screenshots missing
- Check `screenshots/run_{id}/` folder
- Verify disk space is available
- Check application logs for save errors

### Next Step button not appearing
- Ensure "Step-by-Step Mode" checkbox is checked
- Button only shows when in PAUSED_STEP state
- If stuck, click "Stop" and restart the crawl

## Development

### Running Tests

```bash
# Unit tests for overlay rendering
pytest tests/unit/test_overlay_renderer.py -v

# Integration tests for step-by-step mode
pytest tests/integration/test_step_by_step.py -v
```

### Key Files

| File | Purpose |
|------|---------|
| `src/mobile_crawler/domain/overlay_renderer.py` | Overlay drawing logic |
| `src/mobile_crawler/core/crawl_state_machine.py` | PAUSED_STEP state |
| `src/mobile_crawler/core/crawler_loop.py` | Step-by-step pause logic |
| `src/mobile_crawler/ui/widgets/crawl_control_panel.py` | Checkbox & Next Step button |
| `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` | Screenshot overlay display |
