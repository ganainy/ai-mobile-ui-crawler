# Feature Specification: Integrate Mailosaur Service

**Feature Branch**: `018-integrate-mailosaur`  
**Created**: 2026-01-15  
**Status**: Draft  
**Input**: User description: "create a new services that use Mailosaur to get the OTP and magic links and SMS when they are required when the crawler signsup and add standalone tests to test them"

## Clarifications

### Session 2026-01-15
- Q: How should the service identify the correct magic link when multiple links exist? → A: Support optional text matching (e.g., "Verify Email") to find the specific link; default to first link if unspecified.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
-->

### User Story 1 - Retrieve OTP from Email (Priority: P1)

The crawler initiates a signup process using a Mailosaur email address. The system needs to retrieve the One-Time Password (OTP) sent to that email to complete the verification step.

**Why this priority**: Essential for basic account creation flows that require email verification via code.

**Independent Test**: Can be fully tested by sending a test email with an OTP to a Mailosaur address and asserting that the service correctly extracts and returns the code.

**Acceptance Scenarios**:

1. **Given** a Mailosaur server ID and API key, **When** the crawler requests an OTP for a specific email address, **Then** the service polls Mailosaur, finds the latest matching email, and returns the OTP code.
2. **Given** no email arrives within the timeout period, **When** the crawler requests an OTP, **Then** the service raises a timeout error or returns a failure status.

---

### User Story 2 - Retrieve Magic Link from Email (Priority: P1)

The crawler initiates a signup process where verification is done via a clickable link (magic link). The system needs to obtain this URL to simulate a click or navigate to it.

**Why this priority**: Critical for supporting standard "click to verify" email flows.

**Independent Test**: Can be tested by sending an email with a verification link and asserting the service extracts the correct URL.

**Acceptance Scenarios**:

1. **Given** a specific email subject or recipient, **When** the crawler requests the verification link, **Then** the service parses the latest email and returns the target URL.

---



---

### User Story 4 - Standalone Integration Testing (Priority: P1)

A developer wants to verify the Mailosaur integration without running the full crawler. They run a dedicated test suite that validates the API interactions.

**Why this priority**: Ensures the integration is robust and debuggable outside the complex crawler environment.

**Independent Test**: Run the specific test file `tests/integration/test_mailosaur_e2e.py`.

**Acceptance Scenarios**:

1. **Given** valid Mailosaur credentials, **When** the standalone tests are executed, **Then** they perform real (or simulated) send/receive operations and pass if the service functions correctly.

### Edge Cases

- What happens when multiple emails match the criteria? The service should return the most recent one.
- How does system handle network errors when contacting Mailosaur? It should retry or fail gracefully with a clear error.
- What happens if the email format is unexpected (no OTP found)? The service should return a specific error indicating analysis failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Service MUST be able to connect to Mailosaur API using provided credentials (API Key, Server ID).
- **FR-002**: Service MUST provide a method to search for emails based on criteria (e.g., sent to address, subject line).
- **FR-003**: Service MUST automatically extract OTP codes from the message body or subject.
- **FR-004**: Service MUST automatically extract verification links (magic links) from the message body, supporting optional anchor text matching to identify the correct URL among multiple candidates.
- **FR-005**: Service MUST support a configurable timeout for waiting for messages to arrive.

- **FR-007**: Standalone tests MUST be provided to verify OTP and Link extraction logic.

### Key Entities *(include if feature involves data)*

- **MailosaurMessage**: Represents the retrieved email, containing subject, body, sender, and extracted metadata (codes, links).
- **SearchCriteria**: Defines how to look for a specific message (e.g., recipient address, time info).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tests can successfully retrieve an OTP from a generated test email in under 30 seconds (network dependent).
- **SC-002**: Tests can successfully extract a verification link from a generated test email.
- **SC-003**: Integration tests in `tests/integration/test_mailosaur_e2e.py` pass 100% of the time when Mailosaur API is available.
- **SC-004**: Service reports a specific error if a message is not found within the timeout, rather than hanging indefinitely.
