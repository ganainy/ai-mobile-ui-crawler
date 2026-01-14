# Data Model: Integrate Gmail Auth

## GmailAutomationConfig
Settings for the Gmail automation engine.

| Field | Type | Description |
|---|---|---|
| `poll_interval_seconds` | `int` | Time between inbox refreshes. |
| `max_wait_seconds` | `int` | Maximum time to wait for an email. |
| `app_switch_delay_seconds` | `float` | Delay after switching apps. |
| `target_account` | `str` | The specific Gmail address to use (e.g., `user@gmail.com`). |
| `capture_screenshots` | `bool` | Whether to save debug screenshots. |

## GmailSearchQuery
Criteria for finding an email.

| Field | Type | Description |
|---|---|---|
| `sender` | `str` | Exact sender address. |
| `sender_contains` | `str` | Partial sender text. |
| `subject_contains` | `str` | Partial subject text. |
| `received_after` | `datetime` | Only consider emails after this time. |
| `is_unread` | `bool` | Filter for unread status. |

## OTPResult
| Field | Type | Description |
|---|---|---|
| `code` | `str` | The extracted numeric/alphanumeric code. |
| `sender` | `str` | Verified sender. |
| `timestamp` | `float` | Extraction time. |

## LinkResult
| Field | Type | Description |
|---|---|---|
| `url` | `str` | The extracted verification link. |
| `clicked` | `bool` | Whether the click was performed. |
