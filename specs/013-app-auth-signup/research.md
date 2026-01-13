# Research: App Authentication and Signup Support

**Feature Branch**: `013-app-auth-signup`  
**Status**: Research Complete

## Research Questions

### 1. App Switching with Appium

**Question**: How to reliably switch between the target app and Gmail app during crawl execution?

**Decision**: Use Appium's `activate_app()` method on the WebDriver instance to switch between apps. Store the target app package before switching, then restore it after Gmail interaction.

**Rationale**: 
- Appium WebDriver has built-in `activate_app(package_name)` method that brings an app to foreground
- The crawler already uses `driver.current_package` to check which app is active (seen in `crawler_loop.py`)
- This is the standard Appium approach for multi-app scenarios
- No need for ADB commands or complex workarounds

**Alternatives Considered**:
- ADB `am start` commands: More complex, requires subprocess calls, less reliable
- Appium `start_activity()`: Requires knowing exact activity, more brittle
- Keeping both apps in foreground: Not possible on Android, only one app can be foreground

**Implementation Notes**:
- Gmail package name: `com.google.android.gm`
- Need to track original target package before switching
- Add wait time after switching to ensure app is fully loaded
- Verify app switch succeeded by checking `current_package`

---

### 2. Gmail OTP Extraction (Image-Only Mode)

**Question**: How to extract OTP codes or find confirmation links from Gmail emails using image-only approach?

**Decision**: Use OCR (Optical Character Recognition) on Gmail screenshots to extract OTP codes, and use AI vision model to identify and click confirmation links.

**Rationale**:
- The crawler already operates in image-only mode, so we must use screenshots
- OCR service already exists in the codebase (`ocr_service.py` based on project structure)
- AI vision model can identify clickable links in email content
- OTP codes are typically displayed as large, clear text in verification emails
- Confirmation links are usually styled as buttons or underlined text

**Alternatives Considered**:
- Gmail API: Requires OAuth setup, complex, not available on device
- Email parsing via IMAP: Requires credentials, not device-native
- XML/DOM access: Violates image-only mode principle

**Implementation Notes**:
- Navigate to Gmail inbox, search for verification emails from target app domain
- Use OCR to extract text from email body, look for 4-8 digit codes
- Use regex patterns to identify OTP codes: `\b\d{4,8}\b` or similar
- For confirmation links: Use AI to identify button/link coordinates, then click
- Handle multiple emails: Sort by date, use most recent verification email
- Timeout after 30 seconds if email not found

---

### 3. Credential Storage Schema

**Question**: How to design database schema for storing encrypted credentials per app package?

**Decision**: Add new `app_credentials` table to `user_config.db` (not `crawler.db`) with package name as key, encrypted credentials as BLOB, and metadata fields.

**Rationale**:
- `user_config.db` already handles encrypted secrets (API keys)
- Keeps user data separate from crawl session data
- Package name is natural key for lookup
- Reuse existing `CredentialStore` encryption infrastructure
- Store as JSON blob: `{"username": "...", "password": "...", "email": "..."}`

**Schema Design**:
```sql
CREATE TABLE app_credentials (
    app_package TEXT PRIMARY KEY,
    encrypted_credentials BLOB NOT NULL,
    created_at TEXT NOT NULL,           -- ISO 8601
    last_used_at TEXT,                   -- ISO 8601, nullable
    last_successful_login_at TEXT,      -- ISO 8601, nullable
    updated_at TEXT NOT NULL             -- ISO 8601
);
```

**Alternatives Considered**:
- Store in `crawler.db`: Mixes session data with user credentials, not appropriate
- Separate file per app: Harder to manage, no query capabilities
- Plain text storage: Security violation, must encrypt

**Implementation Notes**:
- Use `CredentialStore` for encryption (machine-bound keys)
- Store entire credential object as encrypted JSON string
- Update `last_used_at` on every credential lookup
- Update `last_successful_login_at` only on successful authentication
- Delete credentials if login fails (user may have changed password)

---

### 4. Authentication Screen Detection

**Question**: How to detect signup/login screens using visual analysis?

**Decision**: Use AI vision model to analyze screenshots and identify authentication-related UI elements (email fields, password fields, "Sign Up", "Login", "Verify" buttons).

**Rationale**:
- Crawler already uses AI vision model for screen analysis
- Can extend existing prompt to include authentication detection
- Visual patterns are consistent: email/password fields, "Sign Up"/"Login" buttons
- Can detect verification screens: "Enter OTP", "Verify Email" text

**Alternatives Considered**:
- XML/DOM analysis: Violates image-only mode
- Hardcoded package list: Not scalable, requires maintenance
- URL/activity detection: Not available in image-only mode

**Implementation Notes**:
- Add authentication detection to AI prompt context
- Look for keywords in OCR text: "sign up", "login", "register", "verify", "otp", "email verification"
- Detect form fields: email input, password input, OTP input
- Return structured response: `{"requires_auth": true, "auth_type": "signup|login|verify", "needs_email_verification": true}`
- Store detection result in crawl context to avoid re-detection

---

### 5. Test Email Configuration Storage

**Question**: How to store and retrieve test email address from UI?

**Decision**: Add `test_email` field to Settings panel, store as encrypted secret in `user_config.db` using existing `UserConfigStore.set_secret_plaintext()`.

**Rationale**:
- Email is sensitive data, should be encrypted like passwords
- `UserConfigStore` already has `set_secret_plaintext()` / `get_secret_plaintext()` methods
- Settings panel already handles other secrets (API keys, test password)
- Consistent with existing patterns

**Alternatives Considered**:
- Store as plain text setting: Less secure, email could be sensitive
- Environment variable only: Not user-friendly, requires manual setup
- Separate config file: Inconsistent with existing architecture

**Implementation Notes**:
- Add `test_email_input` QLineEdit to SettingsPanel (similar to `test_password_input`)
- Use `set_secret_plaintext("test_email", email)` to save
- Use `get_secret_plaintext("test_email")` to retrieve
- Validate email format before saving (basic regex check)
- Show placeholder: "Enter test email for authentication"

---

### 6. Credential Reuse Flow

**Question**: When and how to check for stored credentials during crawl?

**Decision**: Check for stored credentials at crawl start (before first step) and when authentication screen is detected. If credentials exist, attempt login first; if login fails, fall back to signup.

**Rationale**:
- Proactive check avoids unnecessary signup flows
- Early detection allows immediate login if credentials available
- Fallback to signup ensures crawl can proceed even if credentials invalid
- Update stored credentials after successful signup to replace old ones

**Alternatives Considered**:
- Always attempt signup first: Wastes time, less efficient
- Never reuse credentials: Poor user experience, requires manual intervention
- Check only on login screen: Misses opportunity for early login

**Implementation Notes**:
- Add `CredentialManager.get_credentials(app_package)` method
- Call at crawl initialization: `crawler_loop.run()` start
- Call when auth screen detected: Check if login screen, use stored credentials
- If login succeeds: Continue crawl, update `last_successful_login_at`
- If login fails: Delete old credentials, proceed with signup flow
- After successful signup: Store new credentials, update timestamps

---

## Technology Choices Summary

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| App Switching | Appium `activate_app()` | Standard, reliable, already available |
| OTP Extraction | OCR + Regex | Works with image-only mode, existing OCR service |
| Link Clicking | AI Vision + Coordinates | Consistent with crawler's image-only approach |
| Credential Storage | SQLite + Fernet Encryption | Reuses existing infrastructure, secure |
| Auth Detection | AI Vision Analysis | Leverages existing AI capabilities |
| Email Config | Encrypted Secret Storage | Consistent with other sensitive data |

## Open Questions Resolved

✅ All technical unknowns have been resolved through research and analysis of existing codebase patterns.

## Dependencies Confirmed

- ✅ Appium WebDriver supports `activate_app()` method
- ✅ OCR service exists in codebase for text extraction
- ✅ `CredentialStore` provides encryption infrastructure
- ✅ `UserConfigStore` supports encrypted secret storage
- ✅ AI vision model can be extended for auth detection
- ✅ Settings panel can be extended with new fields
