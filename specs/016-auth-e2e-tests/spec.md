# Feature Specification: Signup and Sign-In End-to-End Tests

**Feature Branch**: `016-auth-e2e-tests`  
**Created**: 2026-01-13  
**Status**: Draft  
**Input**: User description: "i want to test the signup /sign in functionality of the crawler in real life scenario tests"

## Overview

This feature defines a **comprehensive authentication test suite** with a purpose-built Flutter test app that covers real-world signup and sign-in scenarios. The test app will be created to simulate various authentication patterns encountered in production apps, including:

- Basic email/password authentication
- Email OTP (One-Time Password) verification
- Email verification link (click to verify)
- CAPTCHA simulation (test-mode CAPTCHA that the crawler can solve)

The goal is to validate the crawler's ability to handle complex, multi-step authentication flows.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Signup Flow (Priority: P1)

A developer runs an automated test that validates the crawler can complete a basic signup flow: fill in the registration form (name, email, password), accept terms, and reach the authenticated home screen.

**Why this priority**: This is the foundation for all other auth tests. Basic signup must work before testing advanced verification methods.

**Independent Test**: Launch app → Navigate to signup → Fill form → Submit → Verify authenticated state.

**Acceptance Scenarios**:

1. **Given** the test app shows the basic signup screen, **When** valid credentials are entered and submitted, **Then** the user is authenticated within 30 seconds
2. **Given** the signup form requires terms acceptance, **When** the terms checkbox is checked and form submitted, **Then** signup succeeds
3. **Given** signup completes, **When** the test verifies the final state, **Then** "Welcome" or "Home" screen is displayed

---

### User Story 2 - Basic Sign-In Flow (Priority: P1)

A developer runs an automated test that validates the crawler can log in with existing credentials and reach the authenticated state.

**Why this priority**: Sign-in is equally critical as signup for accessing protected app content.

**Independent Test**: Launch app → Navigate to sign-in → Enter credentials → Submit → Verify authenticated state.

**Acceptance Scenarios**:

1. **Given** a test account exists, **When** valid credentials are entered, **Then** authenticated home screen is displayed within 15 seconds
2. **Given** login succeeds, **When** verification is performed, **Then** a success indicator confirms authentication

---

### User Story 3 - Email OTP Verification (Priority: P1)

A developer runs an automated test that validates the crawler can handle email OTP verification during signup. After initial signup, the app displays an OTP entry screen. The test simulates receiving an OTP (via a predictable test OTP like "123456") and entering it.

**Why this priority**: OTP-based verification is extremely common in production apps.

**Independent Test**: Signup → OTP entry screen appears → Enter test OTP → Verify authenticated state.

# FEATURE: Verify Gmail Integration E2E (SUPERSEDED)

> **NOTICE**: This feature has been SUPERSEDED by [019-force-mailosaur-email](../019-force-mailosaur-email/spec.md).
> Gmail-based UI automation for verification has been removed in favor of Mailosaur API integration.

**Acceptance Scenarios**:

1. **Given** signup triggers OTP verification, **When** the correct test OTP is entered, **Then** signup completes and authenticated state is reached
2. **Given** an incorrect OTP is entered, **When** submitting, **Then** an error message is displayed and retry is allowed
3. **Given** the OTP screen is displayed, **When** the test OTP "123456" is entered, **Then** verification succeeds within 20 seconds

---

### User Story 4 - Email Verification Link (Priority: P1)

A developer runs an automated test that validates the crawler can handle "click link to verify" flows. The test app simulates this by:
1. Showing a "Check your email" screen after signup
2. Providing a deep link that simulates clicking the verification link
3. App receives the deep link and completes verification

**Why this priority**: Email verification links are common in production apps and require app-switching or deep link handling.

**Independent Test**: Signup → "Check email" screen → Trigger verification deep link → Verify authenticated state.

**Acceptance Scenarios**:

1. **Given** signup requires email verification, **When** the verification deep link is triggered, **Then** the app transitions to authenticated state
2. **Given** the "Check email" screen is displayed, **When** the user waits without verification, **Then** a "Resend" option is available
3. **Given** verification completes via deep link, **When** the test verifies the final state, **Then** "Welcome" or "Home" screen is displayed

---

### User Story 5 - CAPTCHA Simulation (Priority: P2)

A developer runs an automated test that validates the crawler can handle CAPTCHA challenges. The test app provides a "test mode" CAPTCHA that:
1. Displays a simple challenge (e.g., "Type the word: TESTCAPTCHA")
2. Accepts a known solution that the crawler can enter
3. Proceeds upon correct entry

**Why this priority**: CAPTCHA handling is important for production apps but uses a simulation approach for testing.

**Independent Test**: Navigate to signup with CAPTCHA → Enter CAPTCHA solution → Complete signup.

**Acceptance Scenarios**:

1. **Given** signup includes a CAPTCHA challenge, **When** the correct solution "TESTCAPTCHA" is entered, **Then** form submission proceeds
2. **Given** an incorrect CAPTCHA is entered, **When** submitting, **Then** an error is shown and a new CAPTCHA is generated
3. **Given** CAPTCHA is solved correctly, **When** signup completes, **Then** authenticated state is reached

---

### User Story 6 - Invalid Credentials Handling (Priority: P2)

A developer runs a test that validates error handling for incorrect login attempts.

**Why this priority**: Error handling is important but secondary to successful flows.

**Independent Test**: Navigate to sign-in → Enter wrong password → Verify error message.

**Acceptance Scenarios**:

1. **Given** the sign-in screen is displayed, **When** invalid credentials are entered, **Then** an error message is displayed
2. **Given** login fails, **When** the error is shown, **Then** the app stays on sign-in screen and allows retry

---

### User Story 7 - Combined Multi-Step Flow (Priority: P2)

A developer runs an automated test validating a complete multi-step auth flow: Signup with CAPTCHA → OTP verification → Reach authenticated state.

**Why this priority**: Tests the crawler's ability to handle sequential verification steps.

**Independent Test**: Full flow through CAPTCHA + OTP in a single signup sequence.

**Acceptance Scenarios**:

1. **Given** signup requires CAPTCHA then OTP, **When** both are completed correctly, **Then** authenticated state is reached within 60 seconds

---

### Edge Cases

- ~~What happens when the test email is already registered?~~ **Resolved**: Tests use unique timestamped emails.
- How does the test handle OTP expiration (timeout)?
- What happens if deep link verification fails or times out?
- How does the test retry CAPTCHA on failure?
- What happens when network is slow or disconnected mid-flow?

## Requirements *(mandatory)*

### Functional Requirements

**Basic Auth:**
- **FR-001**: Test app MUST provide basic signup with name, email, password, and terms checkbox
- **FR-002**: Test app MUST provide basic sign-in with email and password
- **FR-003**: Test app MUST navigate to authenticated Home/Hub screen on successful auth

**OTP Verification:**
- **FR-004**: Test app MUST display OTP entry screen after signup when OTP mode is enabled
- **FR-005**: Test app MUST accept a known test OTP value ("123456") for successful verification
- **FR-006**: Test app MUST show error and allow retry for incorrect OTP

**Email Link Verification:**
- **FR-007**: Test app MUST display "Check your email" screen when link verification mode is enabled
- **FR-008**: Test app MUST accept a deep link (e.g., `testapp://verify?token=TESTTOKEN`) to complete verification
- **FR-009**: Test app MUST transition to authenticated state upon receiving valid verification deep link

**CAPTCHA Simulation:**
- **FR-010**: Test app MUST display a CAPTCHA challenge during signup when CAPTCHA mode is enabled
- **FR-011**: Test app MUST accept a known solution ("TESTCAPTCHA") for the CAPTCHA
- **FR-012**: Test app MUST show error and regenerate CAPTCHA on incorrect solution

**Test Suite:**
- **FR-013**: Test suite MUST use existing device_verifier infrastructure
- **FR-014**: Test suite MUST support configurable auth mode selection (basic, OTP, link, CAPTCHA, combined)
- **FR-015**: Test suite MUST capture screenshots on failure for debugging
- **FR-016**: Test suite MUST handle TAB navigation between form fields

### Deep Link Routes

The test app uses deep links with mode parameters to select authentication scenarios:

| Route | Description |
|-------|-------------|
| `testapp://signup` | Basic signup (no additional verification) |
| `testapp://signup?mode=otp` | Signup with OTP verification |
| `testapp://signup?mode=link` | Signup with email link verification |
| `testapp://signup?mode=captcha` | Signup with CAPTCHA challenge |
| `testapp://signup?mode=combined` | Signup with CAPTCHA + OTP (multi-step) |
| `testapp://signin` | Basic sign-in |
| `testapp://verify?token=TESTTOKEN` | Email verification link (simulates user clicking email link) |

### Test App Screen Flow

```
┌─────────────┐
│   Welcome   │ ─── Choose: Signup or Sign-In
└──────┬──────┘
       │
   ┌───┴───┐
   ▼       ▼
┌──────┐ ┌──────┐
│Signup│ │SignIn│
└──┬───┘ └──┬───┘
   │        │   (if valid credentials)
   │        └────────────────────────────┐
   │                                     │
   ▼ (based on mode)                     │
┌──────────────┐  ┌──────────────┐       │
│ CAPTCHA      │─▶│ OTP Entry    │       │
│ (if enabled) │  │ (if enabled) │       │
└──────────────┘  └──────┬───────┘       │
                         │               │
┌──────────────┐         │               │
│ Email Link   │◀────────┘               │
│ "Check Email"│ (if link mode)          │
└──────┬───────┘                         │
       │ (deep link received)            │
       ▼                                 │
┌──────────────┐                         │
│    HOME      │◀────────────────────────┘
│  (Authed)    │
└──────────────┘
```

### Key Entities

- **Test Credentials**: Email, password, name. Signup uses timestamped emails. Sign-in uses `admin@example.com` / `password123`.
- **Auth Mode**: Enum (BASIC, OTP, EMAIL_LINK, CAPTCHA, COMBINED) determining which verification steps are active.
- **OTP Code**: Fixed test value "123456" for predictable testing.
- **CAPTCHA Solution**: Fixed test value "TESTCAPTCHA" for predictable testing.
- **Verification Token**: Deep link parameter `token=TESTTOKEN` for email link verification.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Basic signup completes in under 30 seconds
- **SC-002**: Basic sign-in completes in under 15 seconds
- **SC-003**: OTP verification flow completes in under 45 seconds
- **SC-004**: Email link verification flow completes in under 45 seconds
- **SC-005**: CAPTCHA + signup flow completes in under 40 seconds
- **SC-006**: Combined multi-step flow completes in under 90 seconds
- **SC-007**: Test suite achieves 95% pass rate on repeated runs
- **SC-008**: All failures include diagnostic screenshots

## Assumptions

- Test app will be created as part of this feature (Flutter/Android)
- Test app location: `test_apps/auth_test_app/` subdirectory in the repository
- Test app uses predictable test values (OTP: "123456", CAPTCHA: "TESTCAPTCHA", Token: "TESTTOKEN")
- Deep links are configured for verification simulation
- Appium server running at localhost:4723
- Device/emulator connected and ready

## Dependencies

- Existing `device_verifier` infrastructure (DeviceSession, GestureHandler, DeepLinkNavigator)
- Flutter SDK for test app creation
- Appium + Android setup

## Out of Scope

- Real email sending/receiving (uses simulated verification)
- Real CAPTCHA services (uses predictable test CAPTCHA)
- Real SMS OTP (uses predictable test OTP)
- OAuth/Social login testing
- Password reset flows
- Biometric authentication

## Clarifications

### Session 2026-01-13

- Q: Signup form fields mismatch - spec says "email, password, confirm password" but app has "name, email, password". Which is correct? → A: Update spec to match app: signup uses Name, Email, Password fields
- Q: What happens when the test email is already registered during signup? → A: Use unique timestamped emails (e.g., `test_1705123456@example.com`) to avoid conflicts
- Q: Test app doesn't exist yet - should spec define real-world auth scenarios? → A: Yes, spec defines comprehensive scenarios (basic, OTP, email link, CAPTCHA) and test app will be created to match
- Q: Which verification methods should the test app support? → A: All: Basic, Email OTP, Email link, CAPTCHA simulation
- Q: How should tests select which auth mode to use? → A: Deep links with mode parameter (e.g., `testapp://signup?mode=otp`, `testapp://signup?mode=captcha`)
- Q: Where should the test app be located? → A: Inside repo at `test_apps/auth_test_app/` subdirectory
