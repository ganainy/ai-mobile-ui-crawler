# Feature Specification: Test App Action Verification

**Feature Branch**: `007-test-app-actions-verify`  
**Created**: 2026-01-11  
**Status**: Draft  
**Input**: User description: "E:\VS-projects\mobile-crawler\TESTAPP_README.md use this is an app installed on the device which i programmed with deep linking to test the appium code the app uses to interact with the device so that i make sure it works , so create a test for each action"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verify Basic Gestures (Tap, Double Tap, Long Press) (Priority: P1)

As a developer, I want to verify that basic touch gestures are correctly interpreted by my Appium code using the dedicated test screens.

**Why this priority**: These are the most fundamental interactions. If these fail, the crawler cannot navigate or interact with basic elements.

**Independent Test**: Can be tested by navigating via ADB deep link intent (e.g., `adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/tap"`) and performing the corresponding actions.

**Acceptance Scenarios**:

1. **Given** the app is on the "Tap" screen via deep link `app://testapp/tap`, **When** a single tap is performed on the target element, **Then** the `success_indicator` accessibility ID must appear on the screen.
2. **Given** the app is on the "Double Tap" screen via deep link `app://testapp/double_tap`, **When** a double tap is performed on the target element, **Then** the `success_indicator` accessibility ID must appear on the screen.
3. **Given** the app is on the "Long Press" screen via deep link `app://testapp/long_press`, **When** a long press is performed on the target element, **Then** the `success_indicator` accessibility ID must appear on the screen.

---

### User Story 2 - Verify Movement Gestures (Drag & Drop, Swipe, Scroll) (Priority: P1)

As a developer, I want to verify that complex movement gestures like dragging, swiping, and scrolling are correctly handled.

**Why this priority**: Movement gestures are essential for navigating lists and rearranging UI elements, which is a key part of mobile app crawling.

**Independent Test**: Can be tested by navigating via ADB deep link intent to `app://testapp/drag_drop`, `app://testapp/swipe`, and `app://testapp/scroll`.

**Acceptance Scenarios**:

1. **Given** the app is on the "Drag & Drop" screen via deep link `app://testapp/drag_drop`, **When** the source element is dragged and dropped onto the target area, **Then** the `success_indicator` accessibility ID must appear.
2. **Given** the app is on the "Swipe" screen via deep link `app://testapp/swipe`, **When** a horizontal or vertical swipe (as indicated) is performed, **Then** the `success_indicator` accessibility ID must appear.
3. **Given** the app is on the "Scroll" screen via deep link `app://testapp/scroll`, **When** a vertical scroll is performed to reveal a hidden element, **And** that element is interacted with or visibility is confirmed, **Then** the `success_indicator` accessibility ID must appear.

---

### User Story 3 - Verify Form Interactions (Input, Slider, Switch, Checkbox, Radio, Dropdown, Stepper) (Priority: P2)

As a developer, I want to verify that various form input types can be interacted with via Appium.

**Why this priority**: Robust form interaction is required for automating tasks like signup, login, and settings configuration.

**Independent Test**: Can be tested by navigating via ADB deep link intent to respective routes (e.g., `app://testapp/input_test`, `app://testapp/slider`).

**Acceptance Scenarios**:

1. **Given** the app is on the "Input" screen via deep link `app://testapp/input_test`, **When** text is typed into the field, **Then** the `success_indicator` accessibility ID must appear.
2. **Given** the app is on the "Slider" screen via deep link `app://testapp/slider`, **When** the slider value is changed to >50, **Then** the `success_indicator` accessibility ID must appear.
3. **Given** the app is on the "Switch/Checkbox/Radio" screen via respective deep links, **When** the toggle or selection state is changed, **Then** the `success_indicator` accessibility ID must appear.
4. **Given** the app is on the "Dropdown" screen via deep link `app://testapp/dropdown`, **When** an item is selected from the list, **Then** the `success_indicator` accessibility ID must appear.
5. **Given** the app is on the "Stepper" screen via deep link `app://testapp/stepper`, **When** the "+" button is tapped 5 times, **Then** the `success_indicator` accessibility ID must appear.

---

### User Story 4 - Verify Dialog Interactions (Alert) (Priority: P2)

As a developer, I want to verify that system or app alerts can be handled.

**Why this priority**: Apps often use alerts for confirmations or errors; the crawler must be able to dismiss or accept them.

**Independent Test**: Can be tested by navigating via ADB deep link intent to `app://testapp/alert`.

**Acceptance Scenarios**:

1. **Given** the app is on the "Alert" screen via deep link `app://testapp/alert`, **When** the "SHOW ALERT" button is tapped and then "OK" is tapped in the dialog, **Then** the `success_indicator` accessibility ID must appear on the underlying screen.

---

### Edge Cases

-   **Timeout**: What happens if the action is performed but the "Success" text doesn't appear within a reasonable timeframe (e.g., 5 seconds)?
-   **Coordinate Precision**: How does the system handle actions performed at the edges of elements?
-   **Interrupted Session**: What happens if the app crashes or the connection is lost during an action test?

## Assumptions

-   **A-001**: The test app is already installed on the target device.
-   **A-002**: Deep linking is correctly configured and working on the target device/OS.
-   **A-003**: The device is accessible via a connection that supports deep link triggers (e.g., ADB for Android).
-   **A-004**: "Success" text is unique enough to serve as a reliable indicator of task completion.

## Requirements *(mandatory)*

### Functional Requirements

-   **FR-001**: The test suite MUST navigate to specific action screens using ADB deep link intents (`adb shell am start -W -a android.intent.action.VIEW -d "app://testapp/{action}"`).
-   **FR-002**: The test suite MUST verify the presence of the `success_indicator` accessibility ID using Appium's `find_element(AppiumBy.ACCESSIBILITY_ID, "success_indicator")`.
-   **FR-003**: The system MUST support individual test execution for each identified action.
-   **FR-004**: The system MUST log the result (Pass/Fail) for each verification attempt.
-   **FR-005**: The system MUST handle navigation failures gracefully (e.g., retry or skip).

### Key Entities *(include if feature involves data)*

-   **TestAction**: Represents an interaction to be verified (e.g., "Tap", "Swipe"). Attributes: Name, DeepLink, TargetElementLocator, ExpectedResult ("Success").
-   **TestResult**: Represents the outcome of a verification. Attributes: ActionName, Status (Pass/Fail), Timestamp, Screenshot (optional).

## Clarifications

### Session 2026-01-12

- Q: How should navigation work between tests? → A: Use ADB deep links to navigate directly to each action screen (e.g., `app://testapp/tap`)
- Q: How should the test return between actions? → A: Each deep link launches the app fresh to the target screen; no hub navigation needed
- Q: How should "Success" verification work? → A: Use Appium accessibility ID detection (`success_indicator`) - more reliable than OCR for Flutter apps
- Q: How should action target coordinates be determined? → A: Use normalized coordinates (0.0-1.0) from TESTAPP_README.md, convert to absolute pixels at runtime
- Q: How should individual action tests be structured? → A: Single file with separate `test_*` functions for each action (run individually via pytest -k)

## Success Criteria *(mandatory)*

### Measurable Outcomes

-   **SC-001**: 100% of the actions listed in the provided documentation have a corresponding automated verification case.
-   **SC-002**: Each verification case completes (from launch to state confirmation) in under 10 seconds on average (excluding device/app startup time).
-   **SC-003**: 100% accuracy in detecting the "Success" state when the interaction is performed correctly.
-   **SC-004**: Verification suite can be run in batch mode to test all actions sequentially without manual intervention.
