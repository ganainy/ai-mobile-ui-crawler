# Feature Specification: Integrate Gmail Auth

**Feature Branch**: `001-integrate-gmail-auth`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "intergate the gmail code that handles OTP and clicking auth links using gmail app into the crawler to use when needed"

## Clarifications

### Session 2026-01-14

- Q: Use cases for the "Valid Gmail Account" field → A: UI Entry & Inbox Verification (Used for form entry and verifying/switching to the correct Gmail inbox).
- Q: Configuration Persistence & Scope → A: Global Settings (Stored alongside "Test Username/Password" in the application's persistent settings panel).
- Q: Handling Multiple Signed-In Accounts → A: Auto-Switch (If multiple accounts exist, crawler must detect and switch to the "Target Gmail Account" via the Gmail UI).
- Q: Display of Sensitive Information → A: Plain Text (The full email address is displayed in the settings for clarity).

## User Scenarios & Testing

### User Story 1 - Automatic OTP Extraction (Priority: P1)

The crawler encounters an authentication screen requiring a One-Time Password (OTP) sent via email. It seamlessly switches to the Gmail app, retrieves the code, and enters it into the application to proceed.

**Why this priority**: Verification is a major blocker for automated crawling of authenticated apps. Solving OTP handling unlocks significant coverage.

**Independent Test**: Can be tested using the existing `auth_test_app` which triggers an OTP email. The test verifies the crawler moves from the OTP entry screen to the authenticated home screen.

**Acceptance Scenarios**:

1. **Given** the crawler is on an OTP entry screen and an email has been sent, **When** the crawler invokes the OTP extraction action, **Then** it switches to Gmail, finds the email, extracts the code, switches back, and enters the code.
2. **Given** no email arrives within the timeout, **When** the crawler waits for OTP, **Then** it reports a failure/timeout and does not crash.

---

### User Story 2 - Magic Link Verification (Priority: P1)

The crawler encounters a "Check your email" screen requiring the user to click a verification link. It switches to Gmail, finds the email, clicks the link, and verifies the app state changes (e.g., deep link opens the app or the app detects verification).

**Why this priority**: many modern apps use magic links or verification links instead of OTPs.

**Independent Test**: Can be tested using `auth_test_app` in "link mode".

**Acceptance Scenarios**:

1. **Given** the crawler is on a "Check email" screen, **When** the crawler invokes the verification link action, **Then** it switches to Gmail, finds the email, clicks the link, and the original app is verified.

### Edge Cases

- **Multiple matching emails**: The system should always select the most recent unread email that matches the criteria.
- **No email arrives**: The system should wait for a configurable timeout and then report failure, rather than hanging indefinitely.
- **Email format variation**: If the OTP or link cannot be found in the email body (e.g., due to responsive design or plain text vs HTML), the system should log the failure and attempt to scroll or read more content if possible, or fail gracefully.
- **Gmail Not Configured**: If the Gmail app is not signed in or shows a welcome screen, the system should catch this state and fail fast with a descriptive error.
- **Account Switching Failure**: If the target account is signed in but the system fails to switch to it via the UI, it should report a failure and not attempt to read from the wrong inbox.

### Assumptions and Dependencies

- **Gmail App**: Assumes the official Gmail Android app is installed and the user is already signed in.
- **Network**: The device must have active internet connectivity to receive emails.
- **Permissions**: The crawler (via ADB/Appium) has permission to force-stop or switch apps.
- **Source Code**: This feature relies on porting existing logic from `tests/integration/device_verifier/gmail`.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST provide a comprehensive Gmail interaction utility in the main source code (`src`) that encapsulates Gmail interactions.
- **FR-002**: The utility MUST support extracting recent OTPs based on sender and subject filters.
- **FR-003**: The utility MUST support clicking verification links based on sender and subject filters.
- **FR-004**: The functionality MUST use the underlying standard Android UI interactions (Appium/ADB) similar to existing tests.
- **FR-005**: The system MUST be able to switch between the target app and Gmail app reliably.
- **FR-006**: Existing tests in `tests/integration/test_auth_gmail_e2e.py` MUST pass using the new source location for the logic, ensuring no regression.
- **FR-007**: The system MUST support a configurable "Target Gmail Account" used to fill signup/login forms and to verify the active account within the Gmail app.
- **FR-008**: The "Target Gmail Account" MUST be persisted in the global application settings UI, alongside other test credentials.
- **FR-009**: The system MUST detect the currently active account in the Gmail app and switch to the "Target Gmail Account" if a mismatch is detected.
- **FR-010**: The "Target Gmail Account" UI field MUST display the email address in plain text to allow user verification.

### Data Model

- **Gmail Automation Config**: Includes polling intervals, timeouts, and the **Target Gmail Account**.

### Success Criteria

### Measurable Outcomes

- **SC-001**: The system successfully extracts 6-digit OTPs from standard test emails 100% of the time in controlled test environments.
- **SC-002**: The system successfully identifies and clicks verification links in standard test emails 100% of the time in controlled test environments.
- **SC-003**: Code duplication between tests and the main app is eliminated.
