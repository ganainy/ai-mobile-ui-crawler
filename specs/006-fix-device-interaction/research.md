# Research: Fix Device Interaction & Add Tests

**Feature Branch**: `006-fix-device-interaction`
**Status**: Research Complete

## Test Target Analysis

We will use the custom Flutter application provided by the user to verify device interactions. This app provides a deterministic environment with standard Input fields, Buttons, and Navigation events.

**App Details (derived from USER context)**:
- **Framework**: Flutter
- **Package Name**: `com.example.flutter_application_1` (inferred from screenshot filenames)
- **Key Flows**:
    1.  **Sign Up Setup**: Enter Name, Email, Password -> Tab agree to terms and conditions -> Tap "Sign Up" -> Expect transition to Sign In.
    2.  **Login Flow**: Enter Email (`admin@example.com`), Password  (`password123`) -> Tap "Sign In" -> Expect "Login Success" screen.

**Element Identifiers (Hypothesis)**:
- Since it's Flutter, standard `id`s might be missing.
- **Strategy**: Use `accessibility_id` (content-desc) or `xpath` looking for text.
    - Fields: "Full Name", "Email Address", "Password".
    - Buttons: "Sign Up", "Sign In".
    - Verification Text: "Login Success", "Welcome Back".

## Implementation Strategy

### 1. Verification Suite (`verify_actions.py`)

We will enforce a dedicated script that runs outside the main crawler loop to isolate Appium issues.
- **Library**: Use standard `Appium-Python-Client`.
- **Structure**: simple `unittest.TestCase` classes.
- **Execution**: `python -m tests.integration.verify_device_actions`

### 2. Appium Driver Refactor

The user reports the current driver is "flaky". We will focus on:
- **Explicit Waits**: Don't rely on implicit sleeps. Wait for element presence/interactability.
- **Coordinates vs Elements**: The crawler often works with VLM coordinates (`tap(x, y)`). The verification suite should test BOTH:
    - **Element-based**: `driver.find_element(...).click()` (Baseline sanity).
    - **Coordinate-based**: Calculate center of element and call `driver.tap_point(x, y)`. This is CRITICAL because the AI often uses coordinates.

### 3. Decisions & Rationale

- **Decision**: Test both Element interactions AND Coordinate interactions.
    - **Rationale**: The AI Agent often outputs coordinates. If we only test `element.click()`, we verify Appium, but not the `tap(x,y)` wrapper the AI uses.
- **Decision**: Hardcode the User's Test App into the verification suite (as a default or option).
    - **Rationale**: It's a known good state. Testing against random apps (the crawler's usual target) is too non-deterministic for a *verification* suite.

## Alternatives Considered

- **Using a System App (Calculator/Settings)**:
    - Pros: Always installed.
    - Cons: Varies wildly by OEM (Samsung vs Pixel vs Xiaomi). Hard to write a universal test.
- **Using the "Current" App**:
    - Pros: Tests what the user is looking at.
    - Cons: Unknown state. Might not have inputs or buttons.
    - **Compromise**: The script will default to the User's Test App but could support a `--current` flag in the future. For this feature, we focus on the Test App.
