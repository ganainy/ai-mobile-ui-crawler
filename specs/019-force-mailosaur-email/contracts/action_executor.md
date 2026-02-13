# Contract: ActionExecutor Email Methods

**Feature**: 019-force-mailosaur-email  
**Date**: 2026-01-15

## Updated Interface

The following methods in `ActionExecutor` are updated to use Mailosaur instead of Gmail.

### extract_otp

**Before (Gmail)**:
```python
def extract_otp(
    self, 
    sender: Optional[str] = None, 
    subject: Optional[str] = None
) -> ActionResult:
    """Execute OTP extraction from Gmail."""
```

**After (Mailosaur)**:
```python
def extract_otp(
    self,
    email: Optional[str] = None,
    timeout: int = 60
) -> ActionResult:
    """
    Execute OTP extraction from Mailosaur.

    Args:
        email: The email address to check for OTP.
               If None, uses configured test email.
        timeout: Maximum time to wait for email (seconds)

    Returns:
        ActionResult with:
        - success=True, input_text=OTP if found
        - success=False, error_message if not found or error
    """
```

### click_verification_link

**Before (Gmail)**:
```python
def click_verification_link(
    self, 
    sender: Optional[str] = None, 
    subject: Optional[str] = None
) -> ActionResult:
    """Execute verification link click in Gmail."""
```

**After (Mailosaur)**:
```python
def click_verification_link(
    self,
    email: Optional[str] = None,
    link_text: Optional[str] = None,
    timeout: int = 60
) -> ActionResult:
    """
    Execute verification link extraction and processing.

    Retrieves the magic link from Mailosaur and opens it using ADB.

    Args:
        email: The email address to check for verification link.
               If None, uses configured test email.
        link_text: Optional anchor text to identify the correct link.
        timeout: Maximum time to wait for email (seconds)

    Returns:
        ActionResult with:
        - success=True if link found and opened
        - success=False, error_message if not found or error
    """
```

## Implementation Notes

### Key Differences

1. **Parameter Changes**:
   - Gmail used `sender` and `subject` filters
   - Mailosaur uses `email` address (recipient) as primary filter

2. **Link Handling**:
   - Gmail: Clicked link in-app, relied on deep link handling
   - Mailosaur: Returns URL string, must be opened externally

3. **Service Dependency**:
   - Gmail: Required Appium driver for UI automation
   - Mailosaur: Pure API calls, no UI automation needed

### Opening Magic Links

When `get_magic_link()` returns a URL, the `ActionExecutor` should:

```python
def click_verification_link(self, email=None, link_text=None, timeout=60):
    # Get the link URL
    try:
        url = self.mailosaur_service.get_magic_link(email, link_text, timeout)
    except Exception as e:
        return ActionResult(success=False, error_message=str(e))
    
    # Open URL via ADB (browser or deep link)
    try:
        self._open_url_via_adb(url)
        return ActionResult(success=True, action_type="click_verification_link")
    except Exception as e:
        return ActionResult(success=False, error_message=f"Failed to open URL: {e}")

def _open_url_via_adb(self, url: str):
    """Open URL on device using ADB."""
    import subprocess
    device_id = self.appium_driver.device_id
    subprocess.run([
        "adb", "-s", device_id,
        "shell", "am", "start",
        "-a", "android.intent.action.VIEW",
        "-d", url
    ], check=True)
```

## Error Cases

| Scenario | ActionResult |
|----------|--------------|
| Mailosaur service not configured | `success=False, error_message="Mailosaur service not configured"` |
| Email not found within timeout | `success=False, error_message="No email received within timeout"` |
| OTP not found in email | `success=False, error_message="No OTP found in email"` |
| Link not found in email | `success=False, error_message="No verification link found"` |
| Link text not matched | `success=False, error_message="No link matching 'X' found"` |
| ADB command failed | `success=False, error_message="Failed to open URL: ..."` |
