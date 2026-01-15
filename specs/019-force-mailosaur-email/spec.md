# Feature Specification: Force Mailosaur for Email Verification

**Feature Branch**: `019-force-mailosaur-email`  
**Created**: 2026-01-15  
**Status**: Draft  
**Input**: User description: "Replace the usage of Gmail for OTP and magic links with Mailosaur, then delete everything related to Gmail including tests. No need for backward compatibility - force use of Mailosaur."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - OTP Extraction via Mailosaur (Priority: P1)

When the mobile crawler performs a signup flow that requires email OTP verification, the system retrieves the OTP code using the Mailosaur service instead of navigating the Gmail Android app.

**Why this priority**: OTP extraction is the most common email verification method. Removing Gmail dependency and using Mailosaur's API is more reliable and faster than UI-based automation.

**Independent Test**: Send a test email with an OTP code to a Mailosaur address and verify the `MailosaurService.get_otp()` method correctly extracts and returns the code within a configurable timeout.

**Acceptance Scenarios**:

1. **Given** valid Mailosaur credentials are configured, **When** the crawler requests an OTP for a Mailosaur email address, **Then** the service polls the Mailosaur API and returns the extracted OTP code.
2. **Given** no email arrives within the timeout period, **When** the crawler requests an OTP, **Then** the service raises a timeout error with a clear message.
3. **Given** an email arrives but contains no recognizable OTP format, **When** the crawler requests an OTP, **Then** the service raises a specific "OTP not found" error.

---

### User Story 2 - Magic Link Extraction via Mailosaur (Priority: P1)

When the mobile crawler performs a signup/login flow that requires clicking a verification link (magic link), the system retrieves the link URL using the Mailosaur service.

**Why this priority**: Magic link verification is equally critical as OTP. The system must support both verification methods with the same reliability guarantees.

**Independent Test**: Send a test email with a verification link to a Mailosaur address and verify the `MailosaurService.get_magic_link()` method correctly extracts and returns the URL.

**Acceptance Scenarios**:

1. **Given** valid Mailosaur credentials are configured, **When** the crawler requests a verification link, **Then** the service polls the Mailosaur API and returns the extracted link URL.
2. **Given** multiple links exist in the email, **When** the crawler requests a link with specific anchor text, **Then** the service returns only the link matching that text.
3. **Given** multiple links exist but no anchor text is specified, **When** the crawler requests a verification link, **Then** the service returns the first link found.

---

### User Story 3 - Complete Gmail Code Removal (Priority: P1)

All Gmail-related code, tests, and configurations are permanently removed from the codebase. The system exclusively uses Mailosaur for email verification with no fallback to Gmail.

**Why this priority**: Technical debt cleanup is essential for maintainability. Gmail automation via Appium/ADB is complex, fragile, and slower than API-based Mailosaur integration.

**Independent Test**: Search the codebase for any remaining Gmail references after deletion. All Gmail imports, classes, and test files should be absent.

**Acceptance Scenarios**:

1. **Given** the migration is complete, **When** grepping the source code for "gmail" or "Gmail", **Then** no matches are found in production code paths.
2. **Given** the migration is complete, **When** running the test suite, **Then** all tests pass without Gmail dependencies.
3. **Given** the migration is complete, **When** inspecting `src/mobile_crawler/infrastructure/`, **Then** no `gmail` directory exists.

---

### User Story 4 - Update ActionExecutor to Use Mailosaur (Priority: P1)

The `ActionExecutor` and related components that previously used `GmailService` are updated to use `MailosaurService` for OTP and verification link extraction.

**Why this priority**: The crawler's core execution loop must use the new service for email verification to work correctly.

**Independent Test**: Mock the Mailosaur service and verify the `ActionExecutor` correctly invokes OTP/link extraction when processing email verification actions.

**Acceptance Scenarios**:

1. **Given** an AI action requires OTP extraction, **When** the ActionExecutor processes the action, **Then** it calls `MailosaurService.get_otp()` with the configured email.
2. **Given** an AI action requires clicking a verification link, **When** the ActionExecutor processes the action, **Then** it calls `MailosaurService.get_magic_link()` and processes the returned URL.

---

### User Story 5 - UI Configuration for Mailosaur (Priority: P2)

The settings panel is updated to allow configuration of Mailosaur credentials (API Key, Server ID) and the test email address. The existing "Test Gmail Account" field is replaced with a Mailosaur-specific configuration.

**Why this priority**: Users need a way to configure Mailosaur credentials through the UI rather than environment variables alone.

**Independent Test**: Open the settings panel and verify Mailosaur configuration fields are present and values persist correctly.

**Acceptance Scenarios**:

1. **Given** the settings panel is open, **When** the user enters Mailosaur credentials, **Then** the values are saved and used by the crawler.
2. **Given** no Mailosaur credentials are configured, **When** the user starts a crawl requiring email verification, **Then** a clear error message indicates missing configuration.

---

### Edge Cases

- What happens when Mailosaur API is unavailable? The service should fail gracefully with a network error message.
- What happens when API credentials are invalid? The service should detect authentication failures and report them clearly.
- What happens if the email body format is unexpected? The service should attempt multiple extraction strategies before failing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST use `MailosaurService` exclusively for OTP extraction during signup/verification flows.
- **FR-002**: System MUST use `MailosaurService` exclusively for magic link extraction during verification flows.
- **FR-003**: System MUST completely remove all Gmail-related code from:
  - `src/mobile_crawler/infrastructure/gmail/` (entire directory)
  - `tests/integration/device_verifier/gmail/` (entire directory)
  - `tests/unit/infrastructure/gmail/` (entire directory)
  - `tests/integration/test_auth_gmail_e2e.py`
- **FR-004**: System MUST update `ActionExecutor` to use `MailosaurService` instead of `GmailService`.
- **FR-005**: System MUST update UI settings to replace Gmail configuration with Mailosaur configuration.
- **FR-006**: System MUST update `main_window.py` to instantiate and inject `MailosaurService` instead of `GmailService`.
- **FR-007**: System MUST update all imports and references that previously used Gmail services.
- **FR-008**: System MUST support configurable timeout for Mailosaur message retrieval.
- **FR-009**: System MUST provide clear error messages when Mailosaur operations fail.

### Key Entities

- **MailosaurService**: Primary service for email verification, providing `get_otp()` and `get_magic_link()` methods.
- **MailosaurConfig**: Configuration model holding API key, server ID, and optional defaults.

## Assumptions

- Mailosaur service implementation from `018-integrate-mailosaur` already exists and is functional.
- The Mailosaur API key and server ID will be provided via environment variables (`MAILOSAUR_API_KEY`, `MAILOSAUR_SERVER_ID`) or UI configuration.
- Existing `MailosaurService` methods (`get_otp`, `get_magic_link`) are sufficient for crawler integration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero Gmail-related files or directories remain in `src/mobile_crawler/infrastructure/`.
- **SC-002**: Zero Gmail-related test files remain in `tests/`.
- **SC-003**: All Mailosaur integration tests in `tests/integration/test_mailosaur_e2e.py` pass.
- **SC-004**: The crawler can successfully complete an OTP verification flow using Mailosaur within 30 seconds.
- **SC-005**: The crawler can successfully extract a magic link using Mailosaur within 30 seconds.
- **SC-006**: No references to "GmailService", "GmailNavigator", "GmailReader", or "GmailAuthVerifier" exist in production code.
- **SC-007**: The application builds and runs without Gmail-related import errors.
