# Data Model: App Authentication and Signup Support

**Feature Branch**: `013-app-auth-signup`  
**Status**: Design Complete

## Database Schema

### app_credentials Table

Stores encrypted authentication credentials for each app package.

**Location**: `user_config.db` (separate from `crawler.db`)

**Schema**:
```sql
CREATE TABLE app_credentials (
    app_package TEXT PRIMARY KEY,           -- Android package name (e.g., 'com.example.app')
    encrypted_credentials BLOB NOT NULL,    -- Encrypted JSON: {"username": "...", "password": "...", "email": "..."}
    created_at TEXT NOT NULL,               -- ISO 8601 timestamp
    last_used_at TEXT,                      -- ISO 8601 timestamp, nullable
    last_successful_login_at TEXT,          -- ISO 8601 timestamp, nullable
    updated_at TEXT NOT NULL                -- ISO 8601 timestamp
);

CREATE INDEX idx_app_credentials_last_used ON app_credentials(last_used_at);
```

**Fields**:
- `app_package`: Primary key, Android package identifier
- `encrypted_credentials`: Encrypted JSON string containing username, password, email
- `created_at`: When credentials were first stored
- `last_used_at`: Last time credentials were retrieved (for any reason)
- `last_successful_login_at`: Last time credentials successfully authenticated
- `updated_at`: Last time credentials were modified (e.g., after signup update)

**Encryption**: Uses `CredentialStore` (Fernet with machine-bound keys), same as API keys

**Example Encrypted Value**:
```json
{
  "username": "testuser123",
  "password": "SecurePass123!",
  "email": "test@example.com"
}
```

---

## Domain Entities

### TestEmailConfiguration

Represents the user-configured test email address for authentication flows.

**Storage**: Encrypted secret in `user_config.db.secrets` table with key `"test_email"`

**Attributes**:
- `email`: String, email address (e.g., "test@example.com")
- `configured_at`: Timestamp when email was set
- `last_used_at`: Timestamp when email was last used for verification

**Validation Rules**:
- Must be valid email format (basic regex: `^[^\s@]+@[^\s@]+\.[^\s@]+$`)
- Cannot be empty
- Stored encrypted using `CredentialStore`

**Access**:
- Set via `UserConfigStore.set_secret_plaintext("test_email", email)`
- Get via `UserConfigStore.get_secret_plaintext("test_email")`

---

### AppAuthenticationCredentials

Represents stored login credentials for a specific app package.

**Storage**: `app_credentials` table in `user_config.db`

**Attributes**:
- `app_package`: String, Android package name (primary key)
- `username`: String, login username
- `password`: String, login password (encrypted)
- `email`: String, email address used for signup
- `created_at`: Timestamp
- `last_used_at`: Timestamp
- `last_successful_login_at`: Timestamp

**Relationships**:
- One-to-one with app package (each package has at most one credential set)

**State Transitions**:
1. **Created**: After successful signup/login, credentials stored
2. **Used**: Credentials retrieved for login attempt
3. **Updated**: After successful signup replaces old credentials
4. **Deleted**: After failed login (credentials invalid)

**Operations**:
- `store(app_package, username, password, email)`: Store new credentials
- `get(app_package)`: Retrieve credentials for app
- `update_last_used(app_package)`: Update last_used_at timestamp
- `update_last_successful(app_package)`: Update last_successful_login_at
- `delete(app_package)`: Remove credentials (e.g., after failed login)

---

### VerificationEmail

Represents an email in Gmail containing verification information (OTP code or confirmation link).

**Storage**: Ephemeral, not persisted (only used during verification flow)

**Attributes**:
- `sender`: String, email sender (usually from target app domain)
- `subject`: String, email subject (often contains "verify", "confirm", "OTP")
- `body_text`: String, extracted email body text (via OCR)
- `otp_code`: String, optional, extracted OTP code (4-8 digits)
- `confirmation_link_present`: Boolean, whether email contains clickable link
- `confirmation_link_coords`: Tuple, optional, (x, y) coordinates of link if present
- `received_at`: Timestamp, when email was received

**Extraction Methods**:
- OTP: Regex pattern `\b\d{4,8}\b` in email body text
- Link: AI vision model identifies clickable button/link coordinates

**Validation**:
- OTP must be 4-8 digits
- Link coordinates must be within screen bounds
- Email must be from expected sender domain (target app)

---

### AuthenticationState

Represents the current authentication state during a crawl session.

**Storage**: In-memory only, part of crawl context

**Attributes**:
- `requires_auth`: Boolean, whether current screen requires authentication
- `auth_type`: Enum, `"signup" | "login" | "verify" | "none"`
- `needs_email_verification`: Boolean, whether email verification is required
- `has_stored_credentials`: Boolean, whether credentials exist for this app
- `verification_in_progress`: Boolean, whether currently retrieving verification from Gmail
- `credentials_used`: Boolean, whether stored credentials were attempted this session

**State Machine**:
```
[No Auth Needed]
    ↓ (auth screen detected)
[Auth Required]
    ↓ (has stored credentials?)
    ├─ Yes → [Attempt Login]
    │         ├─ Success → [Authenticated]
    │         └─ Failure → [Signup Flow]
    └─ No → [Signup Flow]
              ↓ (email verification needed)
              [Gmail Interaction]
              ↓ (OTP/link retrieved)
              [Verification Complete]
              ↓
              [Authenticated]
```

---

## Data Flow

### Credential Storage Flow

```
1. User completes signup/login successfully
2. AuthManager extracts credentials (username, password, email)
3. CredentialManager.store() called with app_package and credentials
4. Credentials encrypted using CredentialStore
5. Encrypted JSON stored in app_credentials table
6. Timestamps updated (created_at, updated_at, last_successful_login_at)
```

### Credential Retrieval Flow

```
1. Crawler detects authentication screen
2. CredentialManager.get(app_package) called
3. Encrypted credentials retrieved from database
4. Credentials decrypted using CredentialStore
5. Credentials returned to AuthManager
6. last_used_at timestamp updated
7. Credentials used for login attempt
```

### Gmail Verification Flow

```
1. Signup form submitted with test email
2. AuthManager detects email verification needed
3. AppSwitcher switches to Gmail app
4. GmailInteraction locates verification email
5. OCR extracts email body text
6. OTP code extracted via regex OR link coordinates identified via AI
7. AppSwitcher switches back to target app
8. OTP pasted into field OR link clicked
9. Verification completed
```

---

## Validation Rules

### Test Email
- Must match email regex pattern
- Cannot be empty
- Should be accessible via Gmail app on device

### App Credentials
- `app_package` must be valid Android package name format
- `username` cannot be empty
- `password` cannot be empty
- `email` must match email regex pattern
- All fields required when storing

### Verification Email
- Must be from expected sender (target app domain)
- OTP code must be 4-8 digits if present
- Link coordinates must be within screen bounds (0 <= x < width, 0 <= y < height)

---

## Migration Notes

**New Table**: `app_credentials` in `user_config.db`

**Migration Script**: Create migration file `src/mobile_crawler/infrastructure/migrations/002_add_app_credentials.sql`

**Backward Compatibility**: 
- No breaking changes to existing tables
- New table is additive only
- Existing crawls continue to work without credentials
