# Appium Action Test Hub

A simplified Flutter application designed specifically for verifying Appium core actions. Every action scenario is isolated into a single-action screen and includes a clear "Success" text indicator and relative coordinate calibration for easy automation verification.

## 🚀 Quick Launch & Hub Locations

Use these commands to jump to a screen. The **Hub Location** column provides the approximate relative `(x, y)` coordinates for the list items on the Hub screen (useful for testing `tap_at` on the hub).

| Action | Full ADB Deep Link Command |
| :--- | :--- |
| **Tap** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/tap" com.example.flutter_application_1` |
| **Double Tap** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/double_tap" com.example.flutter_application_1` |
| **Long Press** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/long_press" com.example.flutter_application_1` |
| **Drag & Drop** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/drag_drop" com.example.flutter_application_1` |
| **Swipe** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/swipe" com.example.flutter_application_1` |
| **Input** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/input_test" com.example.flutter_application_1` |
| **Slider** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/slider" com.example.flutter_application_1` |
| **Switch** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/switch" com.example.flutter_application_1` |
| **Checkbox** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/checkbox" com.example.flutter_application_1` |
| **Radio** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/radio" com.example.flutter_application_1` |
| **Dropdown** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/dropdown" com.example.flutter_application_1` |
| **Stepper** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/stepper" com.example.flutter_application_1` |
| **Scroll** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/scroll" com.example.flutter_application_1` |
| **Alert** | `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/alert" com.example.flutter_application_1` |

## 🎯 Action Specifications (AI Test Generation)

This table provides everything needed to create an Appium test for each action:

| Test | Deep Link Route | Appium Method | Target (x, y) | Action Details | Success Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tap** | `/tap` | `tap(x, y)` | `(0.50, 0.55)` | Single tap on the button | `content-desc="success_indicator"` exists |
| **Double Tap** | `/double_tap` | `doubleTap(x, y)` or `TouchAction.doubleTap()` | `(0.50, 0.60)` | Double tap on the purple box | `content-desc="success_indicator"` exists |
| **Long Press** | `/long_press` | `longPress(x, y, duration=1000)` | `(0.50, 0.60)` | Long press for ~1 second on orange box | `content-desc="success_indicator"` exists |
| **Drag & Drop** | `/drag_drop` | `drag(from, to)` or `TouchAction` sequence | From: `(0.50, 0.35)` → To: `(0.50, 0.75)` | Drag blue box to grey drop target | `content-desc="success_indicator"` exists |
| **Swipe** | `/swipe` | `swipe(start, end, duration)` | Start: `(0.50, 0.50)` | Swipe in any direction with velocity >500px/s. Example: swipe left `(0.80, 0.50) → (0.20, 0.50)` | `content-desc="success_indicator"` exists |
| **Input** | `/input_test` | `tap(x, y)` then `sendKeys("test")` | `(0.50, 0.55)` | Tap input field, type any non-empty string | `content-desc="success_indicator"` exists |
| **Slider** | `/slider` | `swipe(left, right)` on slider track | Drag from `(0.20, 0.50)` → `(0.80, 0.50)` | Move slider thumb to value >50 | `content-desc="success_indicator"` exists |
| **Switch** | `/switch` | `tap(x, y)` | `(0.50, 0.50)` | Tap the switch toggle to turn ON | `content-desc="success_indicator"` exists |
| **Checkbox** | `/checkbox` | `tap(x, y)` | `(0.50, 0.50)` | Tap the checkbox to check it | `content-desc="success_indicator"` exists |
| **Radio** | `/radio` | `tap(x, y)` | `(0.50, 0.65)` | Tap "Option 2" radio button | `content-desc="success_indicator"` exists |
| **Dropdown** | `/dropdown` | `tap(x, y)` then `tap(option)` | Dropdown: `(0.50, 0.55)`, then any option in popup | 1) Tap dropdown 2) Tap any option (Apple/Banana/Cherry) | `content-desc="success_indicator"` exists |
| **Stepper** | `/stepper` | `tap(x, y)` (repeat 5x) | Plus button: `(0.60, 0.55)` | Tap the "+" button 5 times to reach count=5 | `content-desc="success_indicator"` exists |
| **Scroll** | `/scroll` | `scroll(direction="down")` or `swipe` | Swipe up repeatedly: `(0.50, 0.80) → (0.50, 0.20)` | Scroll down until item 49 is visible | `content-desc="success_indicator"` exists |
| **Alert** | `/alert` | `tap(x, y)` (twice) | Button: `(0.50, 0.65)`, then OK: `(0.75, 0.55)` | 1) Tap "SHOW ALERT" 2) Tap "OK" in dialog | `content-desc="success_indicator"` exists |

### Coordinate Conversion
Coordinates are **normalized (0.0 to 1.0)**. To convert to absolute pixels:
```python
absolute_x = relative_x * screen_width
absolute_y = relative_y * screen_height
```

### Universal Success Check (Python Example)
```python
from appium.webdriver.common.appiumby import AppiumBy

def wait_for_success(driver, timeout=10):
    """Wait for the success_indicator accessibility label to appear."""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "success_indicator"))
    )
```


## 🧪 Calibration & Verification

### 📍 Relative Position Display
To facilitate precise coordinate-based automation, the app displays the **relative coordinates** (x, y) for all key elements.
- **Normalization**: Coordinates are normalized from `0.00` to `1.00` of the screen width and height.
- **Dynamic Updates**: Position labels update as elements layout, allowing you to calibrate taps precisely even on different aspect ratios.
- **Hub List**: The main hub displays each action's relative list position.
- **Action Elements**: Individual buttons (e.g., `TAP HERE (0.50, 0.45)`) and target areas show their own coordinates directly in their text.

### ✅ Success State & Appium Search
Each test screen follows a standard pattern for automated discovery:
1.  **Initial State**: Displays "Wait for [Action]" or similar + coordinates.
2.  **Interaction**: Perform the Appium gesture.
3.  **Success State**: Once complete, the text turns **Green** and the word **"Success"** appears.
4.  **Discovery (Appium)**:
    - **Accessibility Label**: The status element uses the `Semantics` label `success_indicator` when completed, and `status_indicator` while waiting.
    - **Search Strategy**: Search for an element with `content-desc` (Android) or `label` (iOS) equal to `success_indicator`.
    - **Dynamic Value**: The text itself contains the status message and relative coordinates, which can also be verified.

## 🛠 Project Setup

### Build and Install
To apply changes to deep links or project structure:
```powershell
flutter build apk --debug
flutter install --debug
```

### Deep Link Configuration
- **Android**: Configured in `android/app/src/main/AndroidManifest.xml` under `.MainActivity` using `app://testapp` scheme.
- **iOS**: Configured in `ios/Runner/Info.plist` under `CFBundleURLTypes`.

## 📂 Project Structure
- `lib/main.dart`: App entry point and named route definitions.
- `lib/screens/test_hub_screen.dart`: Simplified list-based landing page with position tracking.
- `lib/screens/action_screens.dart`: Consolidated file containing all individual test screens and calibration widgets (`PosText`, `ActionText`).
