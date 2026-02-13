# Contract: GmailInteraction

**Module**: `mobile_crawler.domain.gmail_interaction`  
**Purpose**: Handles interaction with Gmail app to retrieve OTP codes and confirmation links

## Interface

### `class GmailInteraction`

Manages Gmail app interactions for email verification.

#### Constructor

```python
def __init__(
    self,
    appium_driver: AppiumDriver,
    ocr_service: OCRService,
    ai_service: AIInteractionService
) -> None
```

**Parameters**:
- `appium_driver`: Appium driver for device interaction
- `ocr_service`: OCR service for text extraction
- `ai_service`: AI service for link detection

---

### Methods

#### `locate_verification_email(test_email: str, app_package: str, timeout: int = 30) -> bool`

Locates and opens the verification email in Gmail.

**Parameters**:
- `test_email`: Test email address to search
- `app_package`: Target app package (for filtering emails)
- `timeout`: Maximum time to search in seconds (default: 30)

**Returns**: `True` if email found and opened, `False` otherwise

**Behavior**:
1. Opens Gmail app (assumes already switched to Gmail)
2. Searches inbox for emails from app domain or with verification keywords
3. Opens most recent verification email
4. Waits for email content to load

**Raises**:
- `GmailInteractionError`: If email not found within timeout

---

#### `extract_otp_code(screenshot: bytes) -> Optional[str]`

Extracts OTP code from current Gmail email screen.

**Parameters**:
- `screenshot`: Screenshot of Gmail email view

**Returns**: OTP code string (4-8 digits) if found, `None` otherwise

**Behavior**:
1. Uses OCR to extract text from email body
2. Searches for OTP pattern: `\b\d{4,8}\b`
3. Returns first matching code
4. Validates code is numeric and within length range

---

#### `find_confirmation_link(screenshot: bytes) -> Optional[Tuple[int, int]]`

Finds confirmation/verification link coordinates in email.

**Parameters**:
- `screenshot`: Screenshot of Gmail email view

**Returns**: `(x, y)` coordinates of link if found, `None` otherwise

**Behavior**:
1. Uses AI vision model to analyze screenshot
2. Identifies clickable buttons/links with verification-related text
3. Returns pixel coordinates of link center
4. Validates coordinates are within screen bounds

---

#### `retrieve_verification(test_email: str, app_package: str, timeout: int = 30) -> VerificationResult`

Complete flow to retrieve verification from Gmail.

**Parameters**:
- `test_email`: Test email address
- `app_package`: Target app package
- `timeout`: Maximum time in seconds

**Returns**: `VerificationResult` with OTP code or link coordinates

**Behavior**:
1. Locates verification email
2. Attempts to extract OTP code
3. If OTP not found, attempts to find confirmation link
4. Returns result with either OTP or link coordinates
5. Raises error if neither found

**Raises**:
- `GmailInteractionError`: If verification cannot be retrieved

---

## Data Types

### `VerificationResult`

```python
@dataclass
class VerificationResult:
    success: bool
    otp_code: Optional[str]  # 4-8 digit code if OTP method
    link_coordinates: Optional[Tuple[int, int]]  # (x, y) if link method
    method: Literal["otp", "link", "none"]  # Which method succeeded
    error_message: Optional[str]
```

---

## Error Types

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
gmail_interaction = GmailInteraction(
    appium_driver=driver,
    ocr_service=ocr_service,
    ai_service=ai_service
)

# Retrieve verification (assumes already in Gmail app)
result = gmail_interaction.retrieve_verification(
    test_email="test@example.com",
    app_package="com.example.app",
    timeout=30
)

if result.success:
    if result.method == "otp":
        # Use OTP code
        otp = result.otp_code
        # Paste into verification field
    elif result.method == "link":
        # Click confirmation link
        x, y = result.link_coordinates
        driver.tap_at(x, y)
else:
    # Handle error
    raise GmailInteractionError(result.error_message)
```

---

## Gmail Package

**Package Name**: `com.google.android.gm`

**Assumptions**:
- Gmail app is installed on device
- Gmail app is logged in to test email account
- Verification emails are received in inbox (not spam)
- Email content is visible (not collapsed)

---

## OTP Extraction Patterns

Common OTP patterns to match:
- `\b\d{4}\b` - 4 digit codes
- `\b\d{5}\b` - 5 digit codes
- `\b\d{6}\b` - 6 digit codes (most common)
- `\b\d{8}\b` - 8 digit codes

Keywords that indicate OTP in email:
- "verification code"
- "OTP"
- "one-time password"
- "code is:"
- "your code:"

---

## Link Detection

AI vision model should identify:
- Buttons with text: "Verify", "Confirm", "Activate", "Click here"
- Underlined or styled links
- Large clickable areas in email body

Link coordinates should be:
- Within screen bounds
- Center of clickable element
- Account for email body scroll position
