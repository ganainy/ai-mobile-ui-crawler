# Research: Gmail App Automation for Auth E2E Tests

**Feature**: Gmail-Integrated Auth E2E Tests
**Date**: 2026-01-14
**Status**: Complete

## Research Questions

1. How do we automate the Gmail app on Android via Appium?
2. What are the accessibility IDs and selectors for Gmail app elements?
3. How do we switch between apps reliably in Appium?
4. How do we use the Android clipboard for OTP transfer?
5. What regex patterns work best for OTP extraction?

---

## 1. Gmail App Automation via Appium

### Decision: Use UiAutomator2 with Gmail App Package

**Gmail App Identifiers:**
- Package: `com.google.android.gm`
- Main Activity: `com.google.android.gm.ConversationListActivityGmail`

**Approach:**
- Launch Gmail using `adb shell am start -n com.google.android.gm/.ConversationListActivityGmail`
- Navigate using accessibility IDs and XPath selectors
- Gmail uses Material Design components with generally good accessibility support

### Rationale
- Device-native approach works exactly like a real user
- No API keys, OAuth, or server-side integration required
- Works with any email sender (not just test emails)

### Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| Gmail API | Requires OAuth setup, project registration, API quotas |
| IMAP/POP3 | Requires email credentials in test code, less realistic |
| Email testing service (Mailinator) | Requires internet, may be blocked, less realistic |

---

## 2. Gmail App Element Selectors

### Key Gmail Elements (Android)

| Element | Selector Strategy | Selector Value |
|---------|-------------------|----------------|
| Inbox list item | XPath | `//android.widget.TextView[contains(@text, '{subject}')]` |
| Email subject | Accessibility ID | `com.google.android.gm:id/subject` |
| Email body | XPath | `//android.webkit.WebView` (for HTML emails) OR `//android.widget.TextView` (plain text) |
| Search button | Accessibility ID | `Search` or `com.google.android.gm:id/search` |
| Search input | Class | `android.widget.EditText` |
| Back button | Accessibility ID | `Navigate up` |
| Compose button | Accessibility ID | `Compose` |

### Email Content Extraction

**HTML Emails (most common):**
- Gmail renders HTML emails in a WebView
- Use `driver.find_element(By.XPATH, "//android.webkit.WebView")` 
- Get page source: `element.get_attribute("text")` or scroll and OCR

**Plain Text Emails:**
- Content is in `android.widget.TextView` elements
- Iterate through text views to find OTP or links

### OTP Pattern Detection

```python
import re

OTP_PATTERNS = [
    r'\b(\d{6})\b',           # 6-digit OTP (most common)
    r'\b(\d{4})\b',           # 4-digit OTP
    r'\b(\d{8})\b',           # 8-digit OTP
    r'code[:\s]+(\d{4,8})',   # "code: 123456" or "code 123456"
    r'OTP[:\s]+(\d{4,8})',    # "OTP: 123456"
    r'verification[:\s]+(\d{4,8})',  # "verification: 123456"
]

def extract_otp(text: str) -> Optional[str]:
    for pattern in OTP_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
```

### Verification Link Detection

```python
LINK_PATTERNS = [
    r'(https?://[^\s<>"]+verify[^\s<>"]*)',   # URLs containing "verify"
    r'(https?://[^\s<>"]+confirm[^\s<>"]*)',  # URLs containing "confirm"
    r'(https?://[^\s<>"]+activate[^\s<>"]*)', # URLs containing "activate"
    r'(https?://[^\s<>"]+token=[^\s<>"]*)',   # URLs with token parameter
]

def extract_verification_link(text: str) -> Optional[str]:
    for pattern in LINK_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
```

---

## 3. App Switching in Appium

### Decision: Use ADB `am start` for Reliable Switching

**Switch to Gmail:**
```python
subprocess.run(['adb', '-s', device_id, 'shell', 'am', 'start', 
                '-n', 'com.google.android.gm/.ConversationListActivityGmail'])
```

**Return to App Under Test:**
```python
subprocess.run(['adb', '-s', device_id, 'shell', 'am', 'start',
                '-n', f'{app_package}/.MainActivity'])
```

**Alternative: Appium's `driver.activate_app(package)`**
```python
driver.activate_app('com.google.android.gm')  # Switch to Gmail
driver.activate_app('com.example.auth_test_app')  # Return to test app
```

### Rationale
- `am start` is more reliable for cold starts
- `activate_app` works well if app is already in recents
- Combine both: use `am start` for initial switch, `activate_app` for subsequent

### Timing Considerations
- Add 1-2 second delay after switching for app to fully load
- Wait for specific element to confirm app is ready before proceeding

---

## 4. Android Clipboard for OTP Transfer

### Decision: Use ADB for Clipboard Operations

**Copy to Clipboard:**
```python
def copy_to_clipboard(device_id: str, text: str):
    # Use am broadcast to set clipboard
    subprocess.run(['adb', '-s', device_id, 'shell', 
                   'am', 'broadcast', '-a', 'clipper.set', '-e', 'text', text])
```

**Alternative: Use Appium Mobile Script:**
```python
driver.execute_script('mobile: setClipboard', {'content': base64.b64encode(text.encode()).decode()})
```

**Paste from Clipboard (in target app):**
1. Tap the input field to focus
2. Long press to show context menu
3. Tap "Paste" option
4. OR use ADB: `adb shell input text "$(adb shell am broadcast -a clipper.get)"`

### Direct Typing Alternative
```python
# If clipboard is unreliable, type directly
def type_otp(driver, device_id: str, otp: str):
    subprocess.run(['adb', '-s', device_id, 'shell', 'input', 'text', otp])
```

### Rationale
- Clipboard is authentic user behavior
- Direct typing works but is slower
- Recommend: Try clipboard first, fall back to typing

---

## 5. Complete Gmail OTP Extraction Workflow

### Recommended Flow

```
1. App under test triggers OTP email
2. Wait configurable delay (default: 10s) for email to arrive
3. Switch to Gmail app
4. Search for email by sender or subject (optional)
5. Tap most recent email in inbox
6. Scroll email to find OTP content
7. Extract OTP using regex patterns
8. Copy OTP to clipboard (or remember in memory)
9. Switch back to app under test
10. Focus OTP input field
11. Paste OTP (or type directly)
12. Submit and verify
```

### Polling for Email Arrival

```python
def wait_for_email(gmail_navigator, sender: str, subject: str, timeout: int = 60) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        gmail_navigator.refresh_inbox()
        if gmail_navigator.find_email(sender=sender, subject=subject):
            return True
        time.sleep(5)  # Check every 5 seconds
    return False
```

---

## 6. Link Click Flow for Email Verification

### Recommended Flow

```
1. App under test shows "Check your email" screen
2. Wait for email arrival
3. Switch to Gmail app
4. Open verification email
5. Find verification link/button in email
6. Tap the link (opens app via deep link)
7. App automatically transitions to authenticated state
8. Verify authentication success
```

### Finding Links in Gmail

**Option A: Tap visible "Verify" button**
```python
verify_button = driver.find_element(By.XPATH, "//android.widget.Button[contains(@text, 'Verify')]")
verify_button.click()
```

**Option B: Tap hyperlink text**
```python
link = driver.find_element(By.XPATH, "//android.widget.TextView[contains(@text, 'click here')]")
link.click()
```

**Option C: Extract URL and trigger via ADB**
```python
url = extract_verification_link(email_content)
subprocess.run(['adb', 'shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', url])
```

---

## 7. Error Handling & Edge Cases

| Scenario | Handling |
|----------|----------|
| Email not arrived | Poll with timeout, clear error message |
| Gmail not signed in | Fail fast with setup instructions |
| Multiple matching emails | Select most recent by position (first in list) |
| OTP not found in email | Log email content, fail with pattern suggestions |
| Link click doesn't open app | Extract URL and use ADB deep link |
| App state lost on return | Re-navigate to OTP input screen |

---

## 8. Gmail Selectors Deep Dive (2026 Android Gmail)

### Inbox View

```
Resource IDs:
- com.google.android.gm:id/recycler_view          # Email list
- com.google.android.gm:id/conversation_list_item # Individual email row
- com.google.android.gm:id/subject                # Email subject text
- com.google.android.gm:id/senders                # Sender name
- com.google.android.gm:id/snippet                # Email preview

Accessibility:
- Search button: "Search in mail"
- Compose: "Compose"
- Navigation drawer: "Open navigation drawer"
```

### Email Detail View

```
Resource IDs:
- com.google.android.gm:id/webview                # HTML content
- com.google.android.gm:id/subject_and_folder_view # Subject header
- com.google.android.gm:id/sender_name            # Sender

HTML Content:
- Email body often wrapped in android.webkit.WebView
- May need to extract text via page_source or OCR
- Links may be in android.widget.TextView or HTML anchors
```

---

## Summary

### Key Decisions

| Topic | Decision | Confidence |
|-------|----------|------------|
| Gmail automation | Use Appium + UiAutomator2 with Gmail app UI | High |
| App switching | ADB `am start` + Appium `activate_app` | High |
| OTP extraction | Regex patterns on email body text | High |
| OTP transfer | Clipboard (Appium) → Paste in app | Medium |
| Link clicking | Tap in Gmail OR extract URL + ADB deep link | Medium |
| Email polling | 5-second intervals, 60-second timeout | Medium |

### Next Steps

1. Create `gmail/gmail_navigator.py` with Gmail app automation
2. Create `gmail/gmail_reader.py` with OTP/link extraction
3. Update `auth_form_filler.py` with clipboard paste
4. Add real-email test cases to `test_auth_e2e.py`
5. Document Gmail setup requirements in `quickstart.md`
