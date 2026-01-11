# Feature Specification: Fix Device Interaction & Add Tests

**Feature Branch**: `006-fix-device-interaction`  
**Created**: 2026-01-11  
**Status**: Draft  
**Input**: User description: "the code that interacts with the device doesnt seem to be working properly, also need some tests that run on the actual device and test that action succeed so that i dont always waste ai token to taste appium actions on device work or not"

## Clarifications

### Session 2026-01-11
- Q: Scope of Test Actions → A: **Coordinates Only** (Tests only `tap_at(x,y)`, `swipe(x1,y1,x2,y2)`, etc. Closest to pure AI mimicry.)
- Q: Removal of UI Element Taps → A: **Confirmed**. `tap(UIElement)` will be removed/ignored in favor of `tap_at(x,y)` as the system relies on vision/VLM coordinates, not XML elements.
- Q: How to test Swipe/Scroll without content? → A: **Test App Updated**. User added `LongListScreen` with 100 scrollable items to verify scroll gestures.
- Q: How to test Drag/Double Tap? → A: **Test App Updated**. User added `PlaygroundScreen` with draggable element, double-tap target, triple-tap target, and long-press target.

## Test App Reference

The verification suite uses a custom Flutter application (`com.example.flutter_application_1`) with purpose-built screens for testing:

| Screen | Package Activity Hint | Testable Actions |
|--------|----------------------|------------------|
| **PlaygroundScreen** | `.PlaygroundScreen` | Single Tap, Double Tap, Triple Tap, Long Press, Drag & Drop |
| **GesturesScreen** | `.GesturesScreen` | Pinch Zoom, Rotate, Pan/Drag, Multi-Touch, Fling/Swipe |
| **LongListScreen** | `.LongListScreen` | Scroll (Vertical), Fling, Swipe-to-Dismiss |
| **FormElementsScreen** | `.FormElementsScreen` | Text Input, Slider, Switch, Checkbox, Radio, Dropdown |
| **SignupScreen** | `.SignupScreen` | Text Input (Name, Email, Password), Button Tap |
| **SigninScreen** | `.SigninScreen` | Text Input (Email, Password), Button Tap |

**Source Reference**: `old-project-for-refrence/docs/test-app-reference/`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Device Action Verification Suite (Priority: P1)

As a developer, I want to run a dedicated test suite against the connected physical device that verifies all core Appium actions actually work as expected **using specific coordinate-based logic to mimic AI behavior**.

**Why this priority**: Currently, basic interactions are unreliable ("doesn't seem to be working properly"). Verifying them with a cheap local test suite prevents wasting expensive AI tokens on failed attempts during live crawls.

**Independent Test**: Can be tested by running the new test script (e.g., `python verify_actions.py`) with a connected device and observing the device perform the requested actions successfully.

**Acceptance Scenarios**:

1. **Given** a connected Android device and running Appium server, **When** I run the verification suite for `tap_at`, **Then** the system taps the "Single Tap" button on PlaygroundScreen by coordinates and verifies a snackbar appears.
2. **Given** the verification suite running, **When** it tests `double_tap`, **Then** it performs two taps in quick succession on the "Double Tap Me!" area and verifies the counter increments.
3. **Given** the verification suite running, **When** it tests `long_press`, **Then** it holds a press on the "Long Press Me!" area and verifies the progress bar fills.
4. **Given** the verification suite running, **When** it tests `input`, **Then** it taps a text field (SignupScreen) by coordinates, sends keys, and verifies the text appears.
5. **Given** the verification suite running, **When** it tests `swipe` or `scroll`, **Then** it performs a vertical swipe on LongListScreen using start/end coordinates and verifies the scroll position chip changes (e.g., "Top" → "Middle").
6. **Given** the verification suite running, **When** it tests `drag`, **Then** it drags the purple "Drag Me" box to the "Drop Here" zone on PlaygroundScreen and verifies the drop count increments.
7. **Given** the verification suite running, **When** it tests `back` button, **Then** the device navigates back from SigninScreen to SignupScreen.
8. **Given** any action fails, **When** the test runs, **Then** it reports the specific action that failed.

---

### User Story 2 - Robust Appium Driver Implementation (Priority: P1)

As a system, the Appium interaction layer must be robust enough to handle the nuances of the physical device, ensuring that when the AI requests an action **(almost always via coordinates)**, it executes faithfully.

**Why this priority**: The user spec states the current code "doesn't seem to be working properly." The implementation must be fixed to pass the verification suite.

**Independent Test**: The same verification suite from Story 1 serves as the integration test for this story.

**Acceptance Scenarios**:

1. **Given** a valid coordinate, **When** `tap_at` is called, **Then** the driver reliably triggers a tap event on the device without error.
2. **Given** a text field focused (via prior tap), **When** `input` is called, **Then** the driver enters the text correctly.
3. **Given** start/end coordinates, **When** `swipe` is called, **Then** the driver executes a smooth gesture that triggers the scroll event.
4. **Given** a drag start and end coordinate pair, **When** `drag` is called, **Then** the driver executes a drag gesture.

---

### Edge Cases

- **Device Locked/Off**: What happens if the test starts when the device is locked? (Should fail fast or wake device).
- **Appium Not Running**: What happens if the server is down? (Should report connection error).
- **Test App Not Installed**: If the app is not installed, the suite should report a clear error.
- **Test App Wrong Screen**: If the app opens to an unexpected screen, relevant tests should skip or fail gracefully with a message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a standalone script/module to run integration tests on the physical device.
- **FR-002**: The `tap_at(x,y)` action implementation MUST be verified using PlaygroundScreen's "Single Tap" button.
- **FR-003**: The `double_tap` action MUST be verified using PlaygroundScreen's "Double Tap Me!" area.
- **FR-004**: The `long_press` action MUST be verified using PlaygroundScreen's "Long Press Me!" area.
- **FR-005**: The `input` (text entry) action MUST be verified using FormElementsScreen or SignupScreen text fields.
- **FR-006**: The `swipe`/`scroll` action MUST be verified using LongListScreen (100-item list).
- **FR-007**: The `drag` action MUST be verified using PlaygroundScreen's Drag & Drop section.
- **FR-008**: The `back` navigation action MUST be verified.
- **FR-009**: The test suite MUST provide clear pass/fail output for each action type.
- **FR-010**: The Appium driver MUST be refactored/fixed if any action fails the verification test.
- **FR-011**: The implementation MUST NOT rely on `find_element` or XML hierarchy for interactions, strictly using coordinates.

### Key Entities

- **DeviceActionVerifier**: A class/module responsible for orchestrating the tests.
- **TestReport**: A simple summary of which actions passed/failed.
- **TestApp**: The `com.example.flutter_application_1` Flutter app serving as the deterministic test target.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of supported actions (Tap, DoubleTap, LongPress, Input, Swipe, Drag, Back) pass the verification suite on the target device.
- **SC-002**: The verification suite completes execution in under 3 minutes (expanded test scope).
- **SC-003**: Integration tests can be run on-demand via a simple CLI command.
