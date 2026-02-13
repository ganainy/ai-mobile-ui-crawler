# Quickstart: Test App Action Verification

**Branch**: `007-test-app-actions-verify`

## Prerequisites

### 1. Ensure Appium is Running

```bash
npx appium -p 4723 --relaxed-security
```

### 2. Ensure Test App is Installed

The Flutter test app (`com.example.flutter_application_1`) must be installed on the connected Android device with deep link support configured.

### 3. Verify Device Connection

```bash
adb devices
# Should show your device as "device" (not "offline")
```

### 4. Test Deep Links Work

```bash
# Test that deep links navigate correctly
adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/tap" com.example.flutter_application_1
```

## Running Tests

### Run All Action Tests

```bash
.venv\Scripts\python.exe -m pytest tests/integration/test_action_verification.py -v
```

### Run a Single Action Test

Use pytest's `-k` flag to run specific tests:

```bash
# Test only tap action
.venv\Scripts\python.exe -m pytest tests/integration/test_action_verification.py -k "test_tap" -v

# Test only double tap action
.venv\Scripts\python.exe -m pytest tests/integration/test_action_verification.py -k "test_double_tap" -v

# Test only swipe action
.venv\Scripts\python.exe -m pytest tests/integration/test_action_verification.py -k "test_swipe" -v

# Test multiple specific actions
pytest tests/integration/test_action_verification.py -k "test_tap or test_swipe" -v
```

### Run by Category

```bash
# Basic gestures (tap, double_tap, long_press)
pytest tests/integration/test_action_verification.py -k "tap or long_press" -v

# Movement gestures (drag, swipe, scroll)
pytest tests/integration/test_action_verification.py -k "drag or swipe or scroll" -v

# Form interactions (input, slider, switch, checkbox, radio, dropdown, stepper)
pytest tests/integration/test_action_verification.py -k "input or slider or switch or checkbox or radio or dropdown or stepper" -v
```

## Available Test Functions

| Test Function | Deep Link Route | Action Verified |
|---------------|-----------------|-----------------|
| `test_tap` | `/tap` | Single tap on target |
| `test_double_tap` | `/double_tap` | Double tap on target |
| `test_long_press` | `/long_press` | Long press (~1 second) |
| `test_drag_drop` | `/drag_drop` | Drag element to drop zone |
| `test_swipe` | `/swipe` | Horizontal swipe gesture |
| `test_scroll` | `/scroll` | Vertical scroll to item 49 |
| `test_input` | `/input_test` | Text input to field |
| `test_slider` | `/slider` | Slider value change to >50 |
| `test_switch` | `/switch` | Toggle switch ON |
| `test_checkbox` | `/checkbox` | Check the checkbox |
| `test_radio` | `/radio` | Select Option 2 |
| `test_dropdown` | `/dropdown` | Select from dropdown |
| `test_stepper` | `/stepper` | Tap + button 5 times |
| `test_alert` | `/alert` | Trigger and dismiss alert |

## Test Flow

Each test follows this pattern:

1. **Force Stop App** - Ensure clean state
2. **Navigate via Deep Link** - Use ADB intent to go directly to action screen
3. **Perform Action** - Execute the gesture at specified coordinates
4. **Verify Success** - Check for `success_indicator` accessibility ID

## Success Detection

The tests use **Appium accessibility ID detection** instead of OCR:

```python
# Looks for element with content-desc="success_indicator"
element = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "success_indicator")
```

This is more reliable than OCR because:
- No image processing errors
- Faster (native query vs screenshot + OCR)
- Works with Flutter's Semantics tree

## Troubleshooting

### Deep Link Not Working

1. Verify deep link scheme in AndroidManifest.xml: `app://testapp`
2. Test manually: `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/tap" com.example.flutter_application_1`
3. Check if app needs rebuild: `flutter build apk --debug && flutter install --debug`

### success_indicator Not Found

1. Ensure action was performed correctly
2. Check the Flutter app uses `Semantics(label: 'success_indicator')`
3. Increase timeout in config: `timeout_seconds: 15`
4. Get current status: `success_verifier.get_status_text()`

### Coordinates Not Aligned

If actions don't hit the right spot:

1. Coordinates are normalized (0.0-1.0) - check TESTAPP_README.md
2. Ensure screen dimensions are correct: `device_session.get_screen_dimensions()`
3. Adjust in `action_configs.py`

### App Not Starting

1. Verify app package name: `com.example.flutter_application_1`
2. Force stop first: `adb shell am force-stop com.example.flutter_application_1`
3. Check ADB permissions

## Configuration

Action coordinates and deep link routes are defined in:
```
tests/integration/device_verifier/action_configs.py
```

All coordinates use normalized values (0.0 to 1.0) from TESTAPP_README.md.

## Example Output

```
tests/integration/test_action_verification.py::test_tap PASSED     [ 7%]
tests/integration/test_action_verification.py::test_double_tap PASSED     [14%]
tests/integration/test_action_verification.py::test_long_press PASSED     [21%]
...
```
