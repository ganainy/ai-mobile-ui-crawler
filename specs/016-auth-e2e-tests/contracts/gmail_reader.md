# Gmail Reader Contract

**Module**: `tests/integration/device_verifier/gmail/gmail_reader.py`
**Purpose**: Extract OTP codes and verification links from email content

## Interface

```python
from typing import Optional, List
from dataclasses import dataclass

@dataclass
class OTPResult:
    """Result of OTP extraction."""
    code: str                    # The extracted OTP code (e.g., "123456")
    pattern_matched: str         # Regex pattern that matched
    context: str                 # Text around the OTP for debugging
    confidence: float            # 0.0-1.0 confidence score

@dataclass
class LinkResult:
    """Result of verification link extraction."""
    url: str                     # The verification URL
    link_text: Optional[str]     # Anchor text if available
    link_type: str               # "BUTTON", "TEXT_LINK", "URL_ONLY"
    is_deep_link: bool          # True if app deep link scheme

class GmailReader:
    """Extract OTP codes and verification links from open emails."""
    
    def __init__(self, driver, device_id: str):
        """
        Initialize Gmail content reader.
        
        Args:
            driver: Appium WebDriver instance
            device_id: Android device ID for ADB commands
        """
        pass
    
    def get_email_content(self) -> str:
        """
        Extract text content from currently open email.
        
        Returns:
            Plain text content of the email body
            
        Raises:
            NoEmailOpenError: If no email is currently open
            
        Note:
            May scroll email to capture full content
        """
        pass
    
    def extract_otp(self, custom_patterns: List[str] = None) -> Optional[OTPResult]:
        """
        Extract OTP code from currently open email.
        
        Args:
            custom_patterns: Additional regex patterns to try
            
        Returns:
            OTPResult if found, None otherwise
            
        Default Patterns:
            - 6-digit code (\d{6})
            - 4-digit code (\d{4})
            - "code: NNNNNN" pattern
            - "OTP: NNNNNN" pattern
        """
        pass
    
    def extract_verification_link(self, custom_patterns: List[str] = None) -> Optional[LinkResult]:
        """
        Extract verification link from currently open email.
        
        Args:
            custom_patterns: Additional regex patterns for URLs
            
        Returns:
            LinkResult if found, None otherwise
            
        Default Patterns:
            - URLs containing "verify"
            - URLs containing "confirm"  
            - URLs containing "activate"
            - URLs with "token=" parameter
        """
        pass
    
    def click_verification_link(self) -> bool:
        """
        Find and click the verification link/button in the email.
        
        Returns:
            True if link found and clicked, False otherwise
            
        Side Effects:
            - May switch to app if link is deep link
            - May open browser if HTTP link
            
        Note:
            Searches for common verification buttons first,
            then falls back to finding links in text
        """
        pass
    
    def copy_otp_to_clipboard(self) -> bool:
        """
        Extract OTP and copy it to device clipboard.
        
        Returns:
            True if OTP found and copied, False otherwise
            
        Side Effects:
            - Modifies device clipboard content
        """
        pass
```

## Error Types

```python
class GmailReadError(Exception):
    """Base error for Gmail reading failures."""
    pass

class NoEmailOpenError(GmailReadError):
    """No email is currently open to read."""
    pass

class OTPNotFoundError(GmailReadError):
    """OTP code not found in email content."""
    pass

class LinkNotFoundError(GmailReadError):
    """Verification link not found in email."""
    pass
```

## Configuration

```python
DEFAULT_OTP_PATTERNS = [
    r'\b(\d{6})\b',                    # Standalone 6 digits
    r'\b(\d{4})\b',                    # Standalone 4 digits
    r'\b(\d{8})\b',                    # Standalone 8 digits
    r'code[:\s]+(\d{4,8})',            # "code: 123456"
    r'OTP[:\s]+(\d{4,8})',             # "OTP: 123456"
    r'verification[:\s]+(\d{4,8})',    # "verification code: 123456"
    r'passcode[:\s]+(\d{4,8})',        # "passcode: 123456"
]

DEFAULT_LINK_PATTERNS = [
    r'(https?://[^\s<>"]+verify[^\s<>"]*)',
    r'(https?://[^\s<>"]+confirm[^\s<>"]*)',
    r'(https?://[^\s<>"]+activate[^\s<>"]*)',
    r'(https?://[^\s<>"]+token=[^\s<>"]*)',
]

VERIFICATION_BUTTON_TEXTS = [
    "Verify",
    "Confirm",
    "Activate",
    "Click here",
    "Verify Email",
    "Confirm Email",
    "Verify your email",
]
```

## Usage Example

```python
# After opening email with GmailNavigator
reader = GmailReader(driver, device_id)

# Option 1: Extract OTP and paste manually
otp = reader.extract_otp()
if otp:
    print(f"Found OTP: {otp.code}")
    reader.copy_otp_to_clipboard()

# Option 2: Click verification link directly
if reader.click_verification_link():
    print("Verification link clicked, waiting for app...")
```
