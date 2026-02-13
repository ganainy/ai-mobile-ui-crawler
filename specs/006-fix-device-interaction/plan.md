# Implementation Plan: Fix Device Interaction & Add Tests

**Branch**: `006-fix-device-interaction` | **Date**: 2026-01-11 | **Spec**: [specs/006-fix-device-interaction/spec.md](spec.md)
**Input**: Feature specification from `/specs/006-fix-device-interaction/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This plan outlines the creation of a **Device Action Verification Suite** (`verify_actions.py`) to systematically test Appium interactions (tap, input, swipe, navigation) against a connected device. It also covers the refactoring of the `AppiumDriver` implementation to pass these tests. We will use a custom-built Flutter application (Sign Up/Sign In flow) provided by the user as the target for these tests, ensuring a consistent and controlled environment for validation.

## Technical Context

**Language/Version**: Python 3.9+ (same as existing codebase)
**Primary Dependencies**: `Appium-Python-Client`, `selenium`
**Testing**: `unittest` or `pytest` (standard python testing)
**Target Platform**: Android (via Appium)
**Project Type**: Python CLI / Backend logic for Mobile Crawler
**Performance Goals**: N/A (Verification suite speed is secondary to reliability, but spec says < 2 min)
**Constraints**: Must run on the physical device currently connected.

**Existing Issues**:
- The current `AppiumDriver` is reported as flaky/broken.
- AI tokens are being wasted on failed attempts.

**Test Target**:
- The user has provided screenshots of a custom Flutter app (`com.example.flutter_application_1` - assumed from screenshot filename/context).
- Screens: "Sign Up Scenario", "Sign In", "Login Success".
- Elements: "Full Name", "Email Address", "Password", "Sign Up" button, "Sign In" button (likely on a home or separate screen), "Welcome Back" text.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Library-First**: The verification logic should be a standalone script or module, consistent with library-first principles.
- **CLI Interface**: The verification suite will be run from the CLI.
- **Test-First**: This entire feature is about enabling a test-first approach for device interactions.

**Status**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/006-fix-device-interaction/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/
└── mobile_crawler/
    ├── infrastructure/
    │   └── appium_driver.py  # Target for refactoring
    └── tools/                # (Potential location for driver, or in infrastructure)

tests/
├── integration/              # New verification suite location
│   └── verify_device_actions.py
└── unit/
    └── test_appium_driver.py # Unit tests for the driver logic itself
```

**Structure Decision**: We will place the verification suite in `tests/integration/` as it requires a live device. Refactoring will happen in `src/mobile_crawler/infrastructure/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |
