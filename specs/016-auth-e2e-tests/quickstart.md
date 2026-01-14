# Quickstart: Gmail-Integrated Auth E2E Tests

## Prerequisites

### 1. Device Setup

- Android device or emulator with Google Play Services
- Gmail app installed and **signed in** to a test Google account
- USB debugging enabled
- Device connected via `adb devices`

### 2. Gmail App Configuration

1. Open Gmail on the device
2. Sign in with a test Google account (e.g., `your-test-account@gmail.com`)
3. Ensure inbox is accessible without additional prompts
4. **Optional**: Disable "Conversation View" for simpler email parsing

### 3. Test Environment

```bash
# Verify device connection
adb devices

# Verify Gmail is installed
adb shell pm list packages | findstr com.google.android.gm

# Verify Gmail can be launched
adb shell am start -n com.google.android.gm/.ConversationListActivityGmail
```

### 4. Python Dependencies

```bash
cd e:\VS-projects\mobile-crawler
pip install appium-python-client selenium
```

### 5. Appium Server

```bash
npx appium --address 127.0.0.1 --port 4723 --relaxed-security
```

---

## Running Gmail-Integrated Tests

### Step 1: Start Appium Server

```bash
- **Physical Device**: Required for Gmail app automation (Emulators often lack Gmail or Google Play Services).
- **Gmail Signed In**: The Gmail app must be signed in to the account that receives verification emails.
- **English/German UI**: Supported (resource IDs are language-agnostic).

## Usage Examples

### OTP Verification Flow

```python
def test_signup_with_otp(gmail_auth_verifier, auth_form_filler):
    # 1. Trigger email in app
    auth_form_filler.fill_signup_form(creds)
    auth_form_filler.submit()
    
    # 2. Verify in Gmail
    otp = gmail_auth_verifier.verify_otp_flow(
        subject="Verification",
        timeout=60
    )
    
    # 3. Enter OTP in app
    if otp:
        auth_form_filler.paste_otp()
        auth_form_filler.submit()
```

### Verification Link Flow

```python
def test_signup_with_link(gmail_auth_verifier, auth_form_filler):
    # 1. Trigger email
    auth_form_filler.fill_signup_form(creds)
    auth_form_filler.submit()
    
    # 2. Click link in Gmail
    success = gmail_auth_verifier.verify_link_flow(
        subject="Verify",
        timeout=60
    )
    
    # 3. App returns to foreground automatically
    assert success
```

---

## Test Configuration

### Gmail Search Patterns

Configure email matching in your test:

```python
# tests/integration/conftest.py or test file

GMAIL_CONFIG = {
    "sender_filter": "noreply@your-app.com",  # Filter by sender
    "subject_filter": "Verification",          # Filter by subject
    "poll_interval": 5,                        # Seconds between checks
    "max_wait": 60,                            # Max seconds to wait
}
```

### OTP Patterns

Default patterns for OTP extraction:

```python
OTP_PATTERNS = [
    r'\b(\d{6})\b',           # 6-digit
    r'code[:\s]+(\d{4,8})',   # "code: 123456"
    r'OTP[:\s]+(\d{4,8})',    # "OTP: 123456"
]
```

---

## Troubleshooting

### Gmail Not Opening

```bash
# Check Gmail is installed
adb shell pm list packages | findstr gmail

# Force stop and relaunch
adb shell am force-stop com.google.android.gm
adb shell am start -n com.google.android.gm/.ConversationListActivityGmail
```

### Gmail Not Signed In

Manually sign in to Gmail on the device before running tests.

### Email Not Found

- Check sender/subject filters match your email
- Increase `max_wait` timeout
- Check spam folder (not currently supported)
- Verify email was actually sent

### OTP Not Extracted

- Check email content format
- Add custom regex patterns for your OTP format
- View email content in debug output

### App Switch Fails

```bash
# Verify both apps are running
adb shell dumpsys activity activities | findstr mResumedActivity
```

---

## Directory Structure

```
tests/integration/device_verifier/
├── gmail/
│   ├── __init__.py
│   ├── gmail_navigator.py    # Gmail app navigation
│   ├── gmail_reader.py       # OTP/link extraction
│   ├── app_switcher.py       # App context switching
│   └── gmail_configs.py      # Selectors and patterns
├── auth/
│   ├── auth_form_filler.py   # Updated with paste support
│   ├── auth_navigator.py
│   ├── auth_verifier.py
│   └── auth_configs.py
└── session.py

tests/integration/
├── test_auth_e2e.py          # Existing simulated tests
└── test_auth_gmail_e2e.py    # NEW: Real Gmail tests
```

---

## Security Notes

⚠️ **Test Account Only**: Use a dedicated test Gmail account, never a personal/production account.

⚠️ **Avoid Storing Credentials**: Don't hardcode Gmail passwords in test code.

⚠️ **Email Content**: Be aware that test emails may contain sensitive information.
