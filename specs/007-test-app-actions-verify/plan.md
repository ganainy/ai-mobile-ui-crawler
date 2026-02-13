# Implementation Plan: Test App Action Verification

**Branch**: `007-test-app-actions-verify` | **Date**: 2026-01-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-test-app-actions-verify/spec.md`

## Summary

Build an isolated, per-action integration test suite for verifying Appium gestures against a dedicated Flutter test app. Each test function will:
1. Navigate directly to the action screen using ADB deep link intent
2. Perform the action on the target screen using normalized coordinates
3. Verify success by detecting the `success_indicator` accessibility ID

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest, appium-python-client, selenium (W3C Actions)
**Storage**: N/A (stateless tests)
**Testing**: pytest with `pytest -k` for individual test selection
**Target Platform**: Android device/emulator via Appium + UiAutomator2
**Project Type**: Single project (test suite extension)
**Performance Goals**: Each test completes in <10 seconds (excluding deep link navigation)
**Constraints**: Flutter app uses accessibility IDs for success detection, coordinate-based gesture interactions
**Scale/Scope**: 14 action tests (tap, double_tap, long_press, drag_drop, swipe, scroll, input, slider, switch, checkbox, radio, dropdown, stepper, alert)

## Constitution Check

*GATE: No constitution violations - this is a test suite enhancement.*

The constitution template is not project-specific. Standard best practices apply:
- ✅ Tests are independently runnable
- ✅ No side effects between tests (app restart strategy)
- ✅ Clear pass/fail criteria (OCR for "Success" text)

## Project Structure

### Documentation (this feature)

```text
specs/007-test-app-actions-verify/
├── plan.md              # This file
├── research.md          # Phase 0 output (OCR/coordinate research)
├── data-model.md        # Phase 1 output (action test data model)
├── quickstart.md        # Phase 1 output (how to run tests)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
tests/integration/
├── conftest.py                     # Existing fixtures (appium_server, android_device)
├── test_action_verification.py     # UPDATED: Uses deep links + accessibility ID verification
└── device_verifier/
    ├── session.py                  # Existing: DeviceSession
    ├── deep_link_navigator.py      # NEW: ADB deep link navigation utility
    ├── success_verifier.py         # NEW: Accessibility ID-based success detection
    └── action_configs.py           # UPDATED: Added deep_link_route field
```

**Structure Decision**: Extend existing `tests/integration/` with deep link navigation and accessibility ID verification. No OCR dependency.

## Phase 0: Research Findings

### Success Detection Strategy

**Decision**: Use Appium accessibility ID detection (`success_indicator`)
**Rationale**: The Flutter test app uses `Semantics` widgets with `label: "success_indicator"` when an action succeeds. This is:
- More reliable than OCR (no image processing errors)
- Faster (native Appium query vs screenshot + OCR)
- Flutter-compatible (accessibility IDs work through Flutter's semantics tree)

**Implementation**:
```python
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def wait_for_success(driver, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "success_indicator"))
    )
```

### Deep Link Navigation Strategy

**Decision**: Use ADB intent with `android.intent.action.VIEW` and `app://testapp/{route}` scheme
**Rationale**: Direct navigation eliminates hub tile coordinate calibration; more reliable than tap-based navigation
**Implementation**:
```python
def navigate_to_action(device_id: str, route: str):
    cmd = [
        'adb', '-s', device_id, 'shell', 'am', 'start', '-W',
        '-a', 'android.intent.action.VIEW',
        '-d', f'app://testapp{route}',
        'com.example.flutter_application_1'
    ]
    subprocess.run(cmd, check=True)
```

### Action Target Coordinates (from TESTAPP_README.md)

All coordinates are normalized (0.0 to 1.0). Convert to absolute pixels: `absolute = relative * screen_dimension`

| Action | Deep Link Route | Target (x, y) | Action Details |
|--------|-----------------|---------------|----------------|
| Tap | `/tap` | `(0.50, 0.55)` | Single tap on button |
| Double Tap | `/double_tap` | `(0.50, 0.60)` | Double tap on purple box |
| Long Press | `/long_press` | `(0.50, 0.60)` | Long press ~1s on orange box |
| Drag & Drop | `/drag_drop` | `(0.50, 0.35)` → `(0.50, 0.75)` | Drag blue box to grey target |
| Swipe | `/swipe` | `(0.80, 0.50)` → `(0.20, 0.50)` | Swipe left with velocity |
| Input | `/input_test` | `(0.50, 0.55)` | Tap field, type text |
| Slider | `/slider` | `(0.20, 0.50)` → `(0.80, 0.50)` | Drag slider to >50 |
| Switch | `/switch` | `(0.50, 0.50)` | Tap switch toggle |
| Checkbox | `/checkbox` | `(0.50, 0.50)` | Tap checkbox |
| Radio | `/radio` | `(0.50, 0.65)` | Tap "Option 2" |
| Dropdown | `/dropdown` | `(0.50, 0.55)` then popup | Tap dropdown, select option |
| Stepper | `/stepper` | `(0.60, 0.55)` x5 | Tap "+" 5 times |
| Scroll | `/scroll` | `(0.50, 0.80)` → `(0.50, 0.20)` | Scroll until item 49 visible |
| Alert | `/alert` | `(0.50, 0.65)` then `(0.75, 0.55)` | Tap button, tap OK |

## Phase 1: Design

### Data Model

**ActionTestConfig** (dataclass for test configuration):
```python
@dataclass
class ActionTestConfig:
    name: str                    # e.g., "tap", "double_tap"
    tile_coords: Tuple[int, int] # Coordinates to tap on hub tile
    action_coords: Tuple[int, int] | None  # Where to perform the action
    action_type: str             # "tap", "double_tap", "long_press", "swipe", "drag", "scroll", "input"
    action_params: Dict[str, Any] # Additional params (end_coords, text, direction, etc.)
    success_text: str = "Success"
    timeout_seconds: int = 5
```

### Internal Contracts

**SuccessVerifier Interface**:
```python
class SuccessVerifier:
    def wait_for_success(self, driver, timeout: int = 10) -> bool:
        """Wait for success_indicator accessibility ID to appear."""
        pass
```

**DeepLinkNavigator Interface**:
```python
class DeepLinkNavigator:
    def navigate_to(self, route: str) -> bool:
        """Navigate directly to action screen via ADB deep link."""
        pass
```

### Test Function Pattern

Each test will follow this pattern:
```python
def test_tap(deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify tap action on dedicated screen."""
    config = ACTION_CONFIGS["tap"]
    width, height = screen_dims
    
    # 1. Navigate directly to action screen via deep link
    deep_link_navigator.navigate_to(config.deep_link_route)
    time.sleep(1)  # Wait for screen to load
    
    # 2. Perform the action
    action_x, action_y = config.get_action_coords(width, height)
    gesture_handler.tap_at(action_x, action_y)
    
    # 3. Verify success_indicator accessibility ID appears
    assert success_verifier.wait_for_success(timeout=5), \
        f"success_indicator not found after {config.name} action"
```

## Complexity Tracking

No constitution violations to justify.

## Next Steps

1. Run `/speckit.tasks` to generate implementation tasks
2. Implement `deep_link_navigator.py` module
3. Implement `success_verifier.py` module
4. Update `action_configs.py` with `deep_link_route` field
5. Update `test_action_verification.py` to use deep links and accessibility ID
6. Remove pytesseract/Pillow dependencies (OCR no longer needed)
