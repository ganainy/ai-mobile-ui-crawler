# Data Model: Integrate Mailosaur Service

**Feature**: Integrate Mailosaur Service
**Date**: 2026-01-15

## Entities

### `MailosaurConfig`
Configuration for the service.
- `api_key`: str
- `server_id`: str

### `MockMessage` (Internal/Testing)
Simplified representation of a Mailosaur message for internal use if needed, but SDK `Message` object will primarily be used.

## Service Interface

### `MailosaurService`

Located in `src/mobile_crawler/infrastructure/mailosaur/service.py`.

#### `__init__(self, api_key: str, server_id: str)`
Initializes the client.

#### `get_otp(self, email: str, timeout: int = 30) -> str`
Retrieves the latest OTP sent to the specified email.
- **Criteria**: sent_to=`email`
- **Logic**: Calls `get_message`, then extracts code using regex or SDK helper (`html.codes` / `text.codes`).
- **Returns**: The first 6-digit (or configured length) code found.

#### `get_magic_link(self, email: str, link_text: Optional[str] = None, timeout: int = 30) -> str`
Retrieves a verification link.
- **Criteria**: sent_to=`email`
- **Logic**: Calls `get_message`, then finds link in `html.links` matching `link_text` if provided, or the first valid verification-looking link.
- **Returns**: URL string.

#### `get_sms_code(self, phone_number: str, timeout: int = 30) -> str`
Retrieves OTP from SMS.
- **Criteria**: sent_to=`phone_number`
- **Logic**: Calls `get_message`, extracts code.
- **Returns**: The code string.

#### `_get_message(self, criteria: SearchCriteria, timeout: int) -> Message`
Internal helper to wrap the SDK call with error handling (Timeout).
