# Contract: AuthManager

**Module**: `mobile_crawler.domain.auth_manager`  
**Purpose**: Orchestrates authentication flows including signup, login, and email verification

## Interface

### `class AuthManager`

Main authentication orchestration class.

#### Constructor

```python
def __init__(
    self,
    appium_driver: AppiumDriver,
    credential_manager: CredentialManager,
    gmail_interaction: GmailInteraction,
    app_switcher: AppSwitcher,
    config_manager: ConfigManager
) -> None
```

**Parameters**:
- `appium_driver`: Appium driver for device interaction
- `credential_manager`: Manager for credential storage/retrieval
- `gmail_interaction`: Handler for Gmail app interactions
- `app_switcher`: Utility for switching between apps
- `config_manager`: Configuration manager for test email

---

### Methods

#### `detect_authentication_required(screenshot: bytes, ocr_text: str) -> AuthenticationState`

Detects if current screen requires authentication.

**Parameters**:
- `screenshot`: Current screenshot bytes
- `ocr_text`: Extracted OCR text from screenshot

**Returns**: `AuthenticationState` with detection results

**Behavior**:
- Analyzes screenshot and OCR text for auth-related UI elements
- Returns state indicating signup/login/verify/none
- Caches result to avoid re-detection

---

#### `handle_authentication(app_package: str, screenshot: bytes, ocr_text: str) -> bool`

Handles authentication flow for current screen.

**Parameters**:
- `app_package`: Target app package name
- `screenshot`: Current screenshot bytes
- `ocr_text`: Extracted OCR text

**Returns**: `True` if authentication successful, `False` otherwise

**Behavior**:
1. Checks for stored credentials
2. If credentials exist, attempts login
3. If login fails or no credentials, proceeds with signup
4. Handles email verification if needed
5. Stores credentials after successful authentication

**Raises**:
- `AuthenticationError`: If authentication fails unrecoverably
- `GmailInteractionError`: If Gmail interaction fails

---

#### `attempt_login_with_stored_credentials(app_package: str, screenshot: bytes) -> bool`

Attempts to log in using stored credentials.

**Parameters**:
- `app_package`: Target app package name
- `screenshot`: Current screenshot bytes

**Returns**: `True` if login successful, `False` otherwise

**Behavior**:
1. Retrieves stored credentials for app
2. Fills login form with credentials
3. Submits form
4. Verifies login success by checking screen state
5. Updates credential timestamps on success

---

#### `handle_signup_flow(app_package: str, test_email: str, screenshot: bytes) -> bool`

Handles signup flow including email verification.

**Parameters**:
- `app_package`: Target app package name
- `test_email`: Test email address for signup
- `screenshot`: Current screenshot bytes

**Returns**: `True` if signup successful, `False` otherwise

**Behavior**:
1. Fills signup form with test email and generated credentials
2. Submits signup form
3. If email verification required, switches to Gmail
4. Retrieves OTP or clicks confirmation link
5. Completes verification
6. Stores credentials after successful signup

---

#### `handle_email_verification(test_email: str, app_package: str) -> VerificationResult`

Handles email verification by interacting with Gmail.

**Parameters**:
- `test_email`: Test email address
- `app_package`: Target app package (for email filtering)

**Returns**: `VerificationResult` with OTP code or link coordinates

**Behavior**:
1. Switches to Gmail app
2. Locates verification email
3. Extracts OTP code or identifies confirmation link
4. Returns verification information
5. Switches back to target app

---

## Data Types

### `AuthenticationState`

```python
@dataclass
class AuthenticationState:
    requires_auth: bool
    auth_type: Literal["signup", "login", "verify", "none"]
    needs_email_verification: bool
    has_stored_credentials: bool
    verification_in_progress: bool
    credentials_used: bool
```

### `VerificationResult`

```python
@dataclass
class VerificationResult:
    success: bool
    otp_code: Optional[str]  # 4-8 digit code if OTP method
    link_coordinates: Optional[Tuple[int, int]]  # (x, y) if link method
    error_message: Optional[str]
```

---

## Error Types

### `AuthenticationError`

Raised when authentication fails unrecoverably.

```python
class AuthenticationError(Exception):
    """Raised when authentication flow fails."""
    pass
```

### `GmailInteractionError`

Raised when Gmail interaction fails.

```python
class GmailInteractionError(Exception):
    """Raised when Gmail app interaction fails."""
    pass
```

---

## Usage Example

```python
# Initialize
auth_manager = AuthManager(
    appium_driver=driver,
    credential_manager=credential_manager,
    gmail_interaction=gmail_interaction,
    app_switcher=app_switcher,
    config_manager=config_manager
)

# Detect auth requirement
state = auth_manager.detect_authentication_required(screenshot, ocr_text)

if state.requires_auth:
    # Handle authentication
    success = auth_manager.handle_authentication(app_package, screenshot, ocr_text)
    if success:
        # Continue crawling
        pass
```
