# Research: Test App Action Verification

**Date**: 2026-01-12
**Branch**: `007-test-app-actions-verify`

## Research Questions

### RQ-1: OCR Library for Flutter Text Detection

**Question**: What is the best approach to detect "Success" text on a Flutter app screen?

**Decision**: `pytesseract` (Python wrapper for Tesseract OCR)

**Rationale**:
- Flutter apps render via Skia engine, making native element trees opaque to Appium
- Screenshot-based OCR is the most reliable approach for Flutter text verification
- Tesseract is mature, well-documented, and handles simple text accurately
- Minimal dependencies: PIL/Pillow for image processing, pytesseract for OCR

**Alternatives Considered**:
| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| EasyOCR | Higher accuracy, supports 80+ languages | Heavy (~1GB models), slow | Overkill for single word detection |
| Google Cloud Vision | Excellent accuracy | Requires API key, network latency, cost | External dependency unacceptable for local tests |
| Appium page source | Native, no extra deps | Flutter elements not exposed reliably | Unreliable for Flutter apps |
| Wait for accessibility labels | Native to Android | Flutter must explicitly set accessibilityLabel | Requires app changes, not universal |

**Implementation Notes**:
```python
# Install dependencies
pip install pytesseract Pillow

# Windows: Install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH or set pytesseract.pytesseract.tesseract_cmd

# Usage
from PIL import Image
import pytesseract

def find_text_in_screenshot(screenshot_base64: str, target_text: str) -> bool:
    img = Image.open(io.BytesIO(base64.b64decode(screenshot_base64)))
    detected_text = pytesseract.image_to_string(img)
    return target_text.lower() in detected_text.lower()
```

---

### RQ-2: App Restart Strategy

**Question**: How to ensure clean app state between tests?

**Decision**: Use ADB `force-stop` + `am start` combination

**Rationale**:
- `force-stop` kills the app process completely, clearing any in-memory state
- `am start` launches the app fresh to its main activity (hub screen)
- Faster than reinstalling the app
- Does not require Appium session restart

**Alternatives Considered**:
| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| Navigate back via UI | Simple | Unreliable, may not reset state | State contamination risk |
| `driver.reset()` (Appium) | Built-in | Deprecated in Appium 2.x, slow | Not recommended |
| Reinstall app | Cleanest state | Very slow (15-30s per test) | Unacceptable test execution time |
| Deep link to hub | Fast | May not reset screen state | State may persist from previous action |

**Implementation**:
```python
import subprocess

def restart_app(device_id: str, app_package: str, main_activity: str) -> bool:
    # Force stop
    subprocess.run(
        ['adb', '-s', device_id, 'shell', 'am', 'force-stop', app_package],
        capture_output=True, timeout=10
    )
    
    # Wait for process to die
    time.sleep(0.5)
    
    # Start fresh
    component = f"{app_package}/{main_activity}"
    result = subprocess.run(
        ['adb', '-s', device_id, 'shell', 'am', 'start', '-n', component],
        capture_output=True, text=True, timeout=10
    )
    
    # Wait for app to stabilize
    time.sleep(2)
    
    return result.returncode == 0
```

---

### RQ-3: Coordinate-Based Tile Navigation

**Question**: How to reliably tap on specific tiles in the hub?

**Decision**: Pre-define fixed coordinates based on device screen dimensions

**Rationale**:
- Flutter app layout is predictable and stable
- Screenshot analysis shows 2-column grid layout
- Coordinates can be calculated as percentage of screen width/height for device-independence

**Screen Analysis** (from provided screenshot):
- Device appears to be ~1080x2400 or similar modern Android resolution
- Hub has 7 rows of tiles (2 per row, except possibly Alert)
- Each tile is approximately 45% of screen width, centered in its column
- Row spacing appears consistent (~150-180px between row centers)

**Coordinate Strategy**:
```python
# Relative positioning (screen percentage)
TILE_POSITIONS = {
    "tap":         (0.25, 0.12),  # Row 1, Left
    "double_tap":  (0.75, 0.12),  # Row 1, Right
    "long_press":  (0.25, 0.20),  # Row 2, Left
    "drag_drop":   (0.75, 0.20),  # Row 2, Right
    "swipe":       (0.25, 0.28),  # Row 3, Left
    "input":       (0.75, 0.28),  # Row 3, Right
    "slider":      (0.25, 0.36),  # Row 4, Left
    "switch":      (0.75, 0.36),  # Row 4, Right
    "checkbox":    (0.25, 0.44),  # Row 5, Left
    "radio":       (0.75, 0.44),  # Row 5, Right
    "dropdown":    (0.25, 0.52),  # Row 6, Left
    "stepper":     (0.75, 0.52),  # Row 6, Right
    "scroll":      (0.25, 0.60),  # Row 7, Left
    "alert":       (0.75, 0.60),  # Row 7, Right
}

def get_tile_coords(action_name: str, screen_width: int, screen_height: int) -> Tuple[int, int]:
    rel_x, rel_y = TILE_POSITIONS[action_name]
    return (int(screen_width * rel_x), int(screen_height * rel_y))
```

**Note**: Coordinates will be validated and fine-tuned during initial calibration run.

---

### RQ-4: Action-Specific Coordinates

**Question**: What coordinates should be used for performing each action on its dedicated screen?

**Decision**: Use screen-center as default target, with action-specific overrides

**Per-Action Analysis**:
| Action | Target Area | Notes |
|--------|-------------|-------|
| Tap | Center of target element | Simple tap at center |
| Double Tap | Center of target element | Two quick taps |
| Long Press | Center of target element | Hold for ~1-2 seconds |
| Drag & Drop | Start at draggable → end at drop zone | Need both start and end coords |
| Swipe | Horizontal across swipe zone | Start right, end left (or vice versa) |
| Scroll | Vertical scroll gesture | Start lower, end upper |
| Input | Tap input field, then send keys | May need keyboard handling |
| Slider | Swipe on slider track | Start at current value, end at target |
| Switch | Tap the switch | Simple tap toggles |
| Checkbox | Tap the checkbox | Simple tap toggles |
| Radio | Tap a radio option | Tap unselected option |
| Dropdown | Tap dropdown, then tap option | Two-step action |
| Stepper | Tap + or - button | Tap increment/decrement |
| Alert | Tap button, then dismiss alert | Two-step: trigger + dismiss |

**Default Target Coordinates**:
```python
# Center of action area (relative to screen)
DEFAULT_ACTION_TARGET = (0.5, 0.5)  # Screen center

# Action-specific adjustments
ACTION_COORDINATES = {
    "drag_drop": {
        "start": (0.5, 0.35),  # Upper area (draggable)
        "end": (0.5, 0.65),    # Lower area (drop zone)
    },
    "swipe": {
        "start": (0.8, 0.5),   # Right side
        "end": (0.2, 0.5),     # Left side
    },
    "scroll": {
        "start": (0.5, 0.7),   # Lower 
        "end": (0.5, 0.3),     # Upper (scroll down reveals content)
    },
    # Others use default center tap
}
```

---

## Summary

All research questions resolved. Ready to proceed with implementation:
1. Add `pytesseract` and `Pillow` to requirements
2. Implement `OCRVerifier` class
3. Implement `AppRestarter` utility
4. Define coordinate configuration file
5. Create individual test functions
