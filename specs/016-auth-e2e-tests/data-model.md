# Data Model: Gmail-Integrated Auth E2E Tests

**Feature**: Gmail OTP/Link Verification
**Date**: 2026-01-14
**Based on**: research.md, plan.md

## Entities

### 1. GmailEmail

Represents an email message in the Gmail inbox.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `sender` | string | Email sender address | Email format |
| `sender_name` | string | Display name of sender | Optional |
| `subject` | string | Email subject line | Non-empty |
| `snippet` | string | Preview text (first ~100 chars) | Optional |
| `body_text` | string | Full plain text content | May be empty for HTML-only |
| `body_html` | string | HTML content if available | Optional |
| `timestamp` | datetime | Email receive time | ISO format |
| `is_read` | boolean | Read/unread status | Default: false |

### 2. OTPExtraction

Result of extracting an OTP code from email content.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `code` | string | Extracted OTP code | 4-8 digits |
| `pattern_matched` | string | Regex pattern that found it | Readonly |
| `context` | string | Text around the OTP | For debugging |
| `confidence` | float | Confidence score (0-1) | 0.0-1.0 |

### 3. VerificationLink

Result of extracting a verification link from email content.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `url` | string | Full verification URL | Valid URL |
| `link_text` | string | Anchor text if available | Optional |
| `link_type` | enum | BUTTON, TEXT_LINK, URL_ONLY | Required |
| `is_deep_link` | boolean | If URL is app deep link | Computed |

### 4. GmailSearchQuery

Parameters for finding emails in Gmail.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `sender` | string | Filter by sender email | Optional |
| `sender_contains` | string | Partial sender match | Optional |
| `subject_contains` | string | Partial subject match | Optional |
| `received_after` | datetime | Emails after this time | Optional |
| `is_unread` | boolean | Only unread emails | Default: true |
| `max_results` | int | Max emails to check | Default: 5 |

### 5. AppContext

Tracks which app is currently active for app switching.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `current_package` | string | Currently active app package | Required |
| `test_app_package` | string | App under test package | Required |
| `gmail_package` | string | Gmail app package | `com.google.android.gm` |
| `previous_activity` | string | Activity before switch | For return |

### 6. ClipboardContent

Android clipboard state for OTP transfer.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `text` | string | Clipboard text content | May be empty |
| `set_at` | datetime | When content was set | Readonly |
| `source` | enum | GMAIL, APP, MANUAL | Readonly |

## State Transitions

### Gmail Email Verification State Machine

```
                                          ┌──────────────────┐
                                          │   EMAIL_SENT     │
                                          │  (app triggers)  │
                                          └────────┬─────────┘
                                                   │
                                                   ▼
   ┌───────────────────────────────────────────────────────────────┐
   │                    WAITING_FOR_EMAIL                           │
   │  (polling Gmail inbox every 5s, timeout 60s)                  │
   └───────────────────────────────────┬───────────────────────────┘
                                       │
                     ┌─────────────────┼─────────────────┐
                     │ Found           │ Timeout         │
                     ▼                 ▼                 │
            ┌────────────────┐   ┌──────────────────┐   │
            │  EMAIL_FOUND   │   │  EMAIL_NOT_FOUND │   │
            └───────┬────────┘   └──────────────────┘   │
                    │                                    │
       ┌────────────┼────────────┐                      │
       │ OTP Mode   │ Link Mode  │                      │
       ▼            ▼            ▼                      │
┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│ OTP_EXTRACT │ │ LINK_CLICK  │ │   FAILED    │◀───────┘
│  (reading)  │ │ (tap link)  │ │             │
└──────┬──────┘ └──────┬──────┘ └─────────────┘
       │               │
       │               │ (deep link triggers app)
       ▼               │
┌─────────────┐        │
│ OTP_COPIED  │        │
│ (clipboard) │        │
└──────┬──────┘        │
       │               │
       ▼               │
┌─────────────┐        │
│ RETURN_APP  │◀───────┘
│ (switch)    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OTP_ENTER / VERIFIED                        │
│  (paste OTP or link clicked → app transitions to auth state)   │
└─────────────────────────────────────────────────────────────────┘
```

## Validation Rules

### OTP Code Validation
- Must be 4-8 digits only
- No leading zeros unless part of the code
- Must match at least one OTP pattern
- Confidence > 0.5 for auto-use, otherwise confirm

### Verification Link Validation
- Must be valid URL format
- Must contain verification-related keywords (verify, confirm, activate, token)
- Deep links must match known app schemes
- HTTPS preferred (warn on HTTP)

### Email Search Validation
- At least one search criterion required (sender, subject, or time)
- `received_after` should be reasonable (not future, not too old)
- `max_results` between 1 and 20

## Configuration

### GmailAutomationConfig

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `gmail_package` | string | `com.google.android.gm` | Gmail app package |
| `poll_interval_seconds` | int | 5 | Time between inbox checks |
| `max_wait_seconds` | int | 60 | Max time to wait for email |
| `otp_patterns` | list[str] | [see research.md] | Regex patterns for OTP |
| `link_patterns` | list[str] | [see research.md] | Regex patterns for links |
| `clipboard_timeout_seconds` | int | 10 | Max time for clipboard op |
| `app_switch_delay_seconds` | float | 1.5 | Delay after app switch |

## Relationships

```
GmailSearchQuery ──────┬──────────→ GmailEmail (0..n)
                       │
OTPExtraction ◀────────┼────────── GmailEmail.body_text
                       │
VerificationLink ◀─────┘────────── GmailEmail.body_text / body_html
                       
AppContext ─────────────────────── tracks current/previous apps

ClipboardContent ◀────────────── OTPExtraction.code (when copying)
```
