# Feature Specification: App Authentication and Signup Support

**Feature Branch**: `013-app-auth-signup`  
**Created**: 2025-01-27  
**Status**: Draft  
**Input**: User description: "i need the app to support apps that require logging in and sign up to crawl them, the crawler opens the gmail app which is logged in to the test email used for crawling (this email will be passed through ui) the app will then copy the OTP or click the confirm register link and then login again, the crawler also need to store this sign in data so that if we crawl again the same app we use it to login and dont have to signupagain"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Test Email for Authentication (Priority: P1)

A user configures a test email address in the UI that will be used for app signup and login flows. This email must be accessible via the Gmail app on the device, and the crawler will use it to retrieve OTP codes and verification links.

**Why this priority**: This is the foundation for all authentication flows. Without a configured test email, the crawler cannot complete signup processes that require email verification.

**Independent Test**: Can be fully tested by adding a test email field to the Settings panel, saving it, and verifying it persists and is accessible to the crawler configuration system.

**Acceptance Scenarios**:

1. **Given** the user opens the Settings panel, **When** they enter a test email address and save, **Then** the email is stored securely and available for crawler use
2. **Given** a test email is configured, **When** the crawler starts, **Then** the test email value is accessible to the authentication system
3. **Given** the user changes the test email, **When** they save settings, **Then** the new email replaces the previous one

---

### User Story 2 - Handle App Signup with Email Verification (Priority: P1)

When the crawler encounters an app requiring signup, it completes the signup form, then switches to the Gmail app to retrieve the verification email (OTP code or confirmation link), completes verification, and returns to the target app to finish the signup process.

**Why this priority**: This is the core functionality that enables crawling apps that require authentication. Without this, the crawler cannot proceed past signup screens.

**Independent Test**: Can be fully tested by crawling an app that requires email verification signup, observing the crawler switch to Gmail, retrieve verification, and complete signup.

**Acceptance Scenarios**:

1. **Given** the crawler encounters a signup screen requiring email verification, **When** it fills the signup form with the test email, **Then** it switches to Gmail app to retrieve the verification
2. **Given** the crawler is in Gmail viewing the verification email, **When** it finds an OTP code or confirmation link, **Then** it extracts the OTP or clicks the link to complete verification
3. **Given** verification is completed via OTP, **When** the crawler returns to the target app, **Then** it pastes the OTP code into the verification field
4. **Given** verification is completed via confirmation link, **When** the link opens the target app, **Then** the crawler continues crawling from the authenticated state
5. **Given** the crawler completes signup and login, **When** it reaches the main app screen, **Then** it stores the authentication credentials for future use

---

### User Story 3 - Reuse Stored Credentials for Subsequent Crawls (Priority: P2)

When crawling an app that has been crawled before and has stored authentication credentials, the crawler uses those credentials to log in directly instead of going through the signup process again.

**Why this priority**: This significantly improves crawl efficiency and user experience by avoiding repeated signup flows. However, it depends on User Story 2 being complete first.

**Independent Test**: Can be fully tested by crawling an app that requires signup (which stores credentials), then crawling the same app again and verifying it uses stored credentials to log in directly.

**Acceptance Scenarios**:

1. **Given** an app has been crawled before and has stored credentials, **When** the crawler starts a new crawl of the same app, **Then** it checks for stored credentials first
2. **Given** stored credentials exist for the app, **When** the crawler encounters a login screen, **Then** it automatically fills and submits the login form using stored credentials
3. **Given** stored credentials are used successfully, **When** the crawler reaches the authenticated state, **Then** it continues crawling without signup flow
4. **Given** stored credentials fail (e.g., expired or invalid), **When** login fails, **Then** the crawler falls back to the signup flow and updates stored credentials

---

### Edge Cases

- What happens when the Gmail app is not installed or not logged in to the test email?
- How does the system handle multiple verification emails in Gmail (e.g., multiple signup attempts)?
- What happens when the OTP code expires before the crawler can use it?
- How does the system handle apps that require additional verification steps beyond email (e.g., SMS, 2FA)?
- What happens when stored credentials become invalid (password changed, account locked)?
- How does the system handle apps that don't use email verification but require other signup methods?
- What happens when the verification email is not found in Gmail within a reasonable time?
- How does the system handle apps that require re-authentication during a crawl session?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a UI field in Settings panel for users to enter and save a test email address
- **FR-002**: System MUST store the test email address securely (encrypted) in user configuration
- **FR-003**: System MUST detect when the target app requires signup or login
- **FR-004**: System MUST switch from target app to Gmail app when email verification is needed
- **FR-005**: System MUST locate and open the verification email in Gmail app
- **FR-006**: System MUST extract OTP codes from verification emails in Gmail
- **FR-007**: System MUST identify and click confirmation/verification links in Gmail emails
- **FR-008**: System MUST return to the target app after retrieving verification information
- **FR-009**: System MUST paste OTP codes into verification fields in the target app
- **FR-010**: System MUST complete the signup and login flow after verification
- **FR-011**: System MUST store authentication credentials (username, password, email) per app package after successful signup/login
- **FR-012**: System MUST encrypt stored authentication credentials for security
- **FR-013**: System MUST check for stored credentials before starting signup flow for a previously crawled app
- **FR-014**: System MUST use stored credentials to automatically log in when available
- **FR-015**: System MUST handle login failures gracefully and fall back to signup flow when stored credentials fail
- **FR-016**: System MUST update stored credentials when signup/login succeeds after a credential failure
- **FR-017**: System MUST associate stored credentials with the app package name for proper retrieval

### Key Entities

- **Test Email Configuration**: Represents the email address configured by the user for authentication flows. Stored securely in user configuration, accessible to crawler during execution.

- **App Authentication Credentials**: Represents stored login credentials (username, password, email) for a specific app package. Includes app package identifier, encrypted credentials, and timestamp of last successful use. Used to skip signup flows on subsequent crawls.

- **Verification Email**: Represents an email in Gmail containing either an OTP code or a confirmation link. The crawler must locate, extract, and use this information to complete email verification flows.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure and save a test email address in the Settings panel, and the value persists across application restarts
- **SC-002**: Crawler successfully completes signup flows requiring email verification for at least 80% of test apps that use standard email verification patterns
- **SC-003**: Crawler retrieves OTP codes or confirmation links from Gmail within 30 seconds of switching to Gmail app in 90% of cases
- **SC-004**: Crawler successfully uses stored credentials to log in directly (skipping signup) for previously crawled apps in at least 85% of subsequent crawl attempts
- **SC-005**: Authentication credentials are stored securely (encrypted) and associated with the correct app package for future retrieval
- **SC-006**: Crawler handles credential failures gracefully, falling back to signup flow and updating stored credentials when login fails but signup succeeds
- **SC-007**: Total time to complete signup flow (including Gmail interaction) is reduced by at least 40% on subsequent crawls when using stored credentials compared to full signup flow

## Assumptions

- The Gmail app is installed on the device and logged in to the test email account
- Test apps use standard email verification patterns (OTP codes or confirmation links in email body)
- The device allows switching between apps (target app and Gmail app) during crawl execution
- Apps store authentication state in a way that persists between app launches (standard session management)
- The test email account is dedicated to crawling and receives verification emails in a timely manner
- Apps use email-based verification as the primary signup method (other methods like SMS or social login are out of scope for this feature)

## Dependencies

- Existing UI Settings panel infrastructure for adding new configuration fields
- Existing credential storage and encryption system for secure data storage
- Existing user configuration storage for persisting user preferences
- Device automation capabilities for switching between apps and interacting with Gmail
- Text extraction capabilities for reading OTP codes from Gmail emails
- Existing crawler loop and action execution system for coordinating app switches

## Out of Scope

- Support for SMS-based verification
- Support for social login (Google, Facebook, etc.)
- Support for apps that require 2FA beyond email verification
- Automatic email account setup or Gmail login
- Support for multiple email accounts or email account switching
- Handling of email providers other than Gmail
- Support for apps that require manual approval or admin activation
- Handling of CAPTCHA or bot detection during signup
