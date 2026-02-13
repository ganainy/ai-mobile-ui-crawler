# Implementation Plan: Gmail-Integrated Auth E2E Tests

**Branch**: `016-auth-e2e-tests` | **Date**: 2026-01-14 | **Spec**: [spec.md](./spec.md)
**Input**: User requirement: "I wanted to use real OTP and email link that is actually sent to my Gmail app and then the crawler opens the Gmail app and does the necessary and then clicks the link or copies the OTP and pastes it in the app"

**Note**: This plan extends the existing simulated auth tests with **real Gmail integration** for OTP and email link verification.

## Summary

Extend the auth E2E test suite to support **real-world email verification workflows**:
- The test app (or any real app under test) sends a real OTP or verification link to the user's Gmail account
- The crawler **switches to the Gmail app** on the device
- The crawler **reads the email content** to extract the OTP or verification link
- The crawler **copies the OTP** or **clicks the verification link**
- The crawler **returns to the app under test** and completes authentication

This enables testing of production-like authentication flows without simulated/hardcoded values.

## Technical Context

**Language/Version**: Python 3.11+ (Test Suite) + Dart/Flutter (Optional Test App)
**Primary Dependencies**: Appium, Android UiAutomator2, Gmail app on device
**Storage**: N/A (stateless test execution)
**Testing**: pytest (Python test suite)
**Target Platform**: Android devices/emulators with Gmail app installed
**Project Type**: Mobile automation test suite
**Performance Goals**: Complete OTP extraction within 60 seconds of email arrival
**Constraints**: Gmail app must be signed in and accessible on test device
**Scale/Scope**: Single Gmail account per test device, one email at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Test-First | ✅ | Tests drive implementation |
| Library-First | ✅ | Gmail automation will be a self-contained module |
| Simplicity | ✅ | No OAuth/API required - uses device-native Gmail UI |
| Integration Testing | ✅ | Real email verification is inherently integration testing |

## Project Structure

### Documentation (this feature)

```text
specs/016-auth-e2e-tests/
├── plan.md              # This file (updated for Gmail integration)
├── research.md          # Research on Gmail app automation
├── data-model.md        # Data model for email extraction
├── quickstart.md        # Quick start guide
├── contracts/           # Internal contracts for Gmail automation
└── tasks.md             # Implementation tasks
```

### Source Code (repository root)

```text
tests/integration/device_verifier/
├── gmail/                     # NEW: Gmail automation module
│   ├── __init__.py
│   ├── gmail_navigator.py     # Navigate to Gmail, search, open emails
│   ├── gmail_reader.py        # Extract OTP/links from email content
│   └── gmail_configs.py       # Gmail-specific selectors and patterns
├── auth/
│   ├── auth_form_filler.py    # Existing - add OTP paste support
│   ├── auth_navigator.py      # Existing - add Gmail app switching
│   ├── auth_verifier.py       # Existing
│   └── auth_configs.py        # Updated with real email patterns
├── deep_link_navigator.py     # Existing - may need app switching
└── session.py                 # Existing - add app context switching
```

### Key New Capabilities

1. **GmailNavigator**: Open Gmail app, navigate to inbox, search for emails by sender/subject
2. **GmailReader**: Scroll email content, extract OTP via regex, extract verification links
3. **App Context Switching**: Switch between app-under-test and Gmail app, return reliably
4. **Link Click Handler**: Tap verification links in Gmail to return to app

## Scope Definition

### In Scope (Phase 1: Gmail Integration)

| ID | Capability | Description |
|----|------------|-------------|
| GM-01 | Open Gmail App | Launch Gmail app from any state |
| GM-02 | Navigate to Inbox | Ensure we're in the inbox view |
| GM-03 | Search Emails | Search by sender and/or subject |
| GM-04 | Open Latest Email | Tap the most recent matching email |
| GM-05 | Extract OTP | Parse 4-8 digit codes from email body |
| GM-06 | Extract Verification Links | Find and tap "Verify" or custom URLs |
| GM-07 | Copy OTP to Clipboard | Use Android clipboard for transfer |
| GM-08 | Paste OTP in App | Return to app and paste copied OTP |
| GM-09 | Click Link in Email | Tap verification link, app handles deep link |
| GM-10 | Return to App | Reliable return to app-under-test after Gmail actions |

### Out of Scope (Future Phases)

- Gmail API/OAuth integration (we use device UI only)
- Multiple Gmail accounts on same device
- Email deletion/management
- Drafts, sent mail, other folders
- Gmail web interface (mobile app only)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gmail UI changes | High | Use accessibility IDs where possible, fall back to text/XPATH |
| Email not arrived yet | Medium | Implement polling with configurable timeout |
| Multiple matching emails | Medium | Always select most recent, optionally filter by timestamp |
| Gmail not signed in | High | Pre-requisite check in test setup, fail fast with clear error |
| App loses state on return | Medium | Use back button or re-launch with state |

## Implementation Phases

### Phase 0: Research
- Gmail app selectors and accessibility structure
- Best practices for app switching in Appium
- Android clipboard API usage
- Email content parsing patterns

### Phase 1: Core Gmail Automation
- Create `gmail/` module with navigator and reader
- Implement OTP extraction with regex patterns
- Implement link extraction and tap
- Add clipboard copy/paste support

### Phase 2: Integration with Auth Tests
- Update `auth_form_filler.py` with paste capability
- Add Gmail-backed test cases to `test_auth_e2e.py`
- Create real email test workflow

### Phase 3: Polish & Resilience
- Add retry logic for email arrival
- Handle Gmail UI variations
- Add comprehensive error reporting

## Complexity Tracking

| Decision | Rationale | Alternative Rejected |
|----------|-----------|---------------------|
| Use Gmail app UI | No API key management, works like real user | Gmail API: requires OAuth setup, project registration |
| Clipboard for OTP | Universal cross-app transfer | Direct typing: requires app focus, slower |
| Search by subject | Most reliable email identification | Chronological: may pick wrong email if multiple arrive |
