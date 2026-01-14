"""
Gmail automation configuration, selectors, and patterns.

This module contains all the constants, selectors, and regex patterns
needed for Gmail app automation.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

# Gmail App Identifiers
GMAIL_PACKAGE = "com.google.android.gm"
GMAIL_ACTIVITY = "com.google.android.gm.ConversationListActivityGmail"

# Gmail UI Element Selectors
GMAIL_SELECTORS = {
    # Inbox view
    "inbox_list": "com.google.android.gm:id/conversation_list",
    "conversation_item": "com.google.android.gm:id/conversation_list_item",
    "email_subject": "com.google.android.gm:id/subject",
    "email_sender": "com.google.android.gm:id/senders",
    "email_snippet": "com.google.android.gm:id/snippet",
    "recycler_view": "com.google.android.gm:id/recycler_view",
    
    # Search
    "search_button": "Search in mail",
    "search_input": "android.widget.EditText",
    "clear_search": "Clear search",
    
    # Navigation
    "navigate_up": "Navigate up",
    "back_button": "Navigate up",
    "compose_button": "Compose",
    "navigation_drawer": "Open navigation drawer",
    
    # Email detail view
    "webview": "com.google.android.gm:id/webview",
    "subject_header": "com.google.android.gm:id/subject_and_folder_view",
    "sender_name": "com.google.android.gm:id/sender_name",
    
    # Verification buttons (common text patterns)
    "verify_button_texts": [
        "Verify",
        "Confirm", 
        "Activate",
        "Click here",
        "Verify Email",
        "Confirm Email",
        "Verify your email",
        "Verify Now",
        "Confirm Now",
    ],
}

# OTP extraction regex patterns
OTP_PATTERNS = [
    r'\b(\d{6})\b',                    # Standalone 6 digits (most common)
    r'\b(\d{4})\b',                    # Standalone 4 digits
    r'\b(\d{8})\b',                    # Standalone 8 digits
    r'code[:\s]+(\d{4,8})',            # "code: 123456" or "code 123456"
    r'OTP[:\s]+(\d{4,8})',             # "OTP: 123456"
    r'verification[:\s]+(\d{4,8})',    # "verification code: 123456"
    r'passcode[:\s]+(\d{4,8})',        # "passcode: 123456"
    r'pin[:\s]+(\d{4,8})',             # "pin: 1234"
    r'one[- ]time[- ]password[:\s]+(\d{4,8})',  # "one-time password: 123456"
]

# Verification link extraction patterns
LINK_PATTERNS = [
    r'(https?://[^\s<>"]+verify[^\s<>"]*)',    # URLs containing "verify"
    r'(https?://[^\s<>"]+confirm[^\s<>"]*)',   # URLs containing "confirm"
    r'(https?://[^\s<>"]+activate[^\s<>"]*)',  # URLs containing "activate"
    r'(https?://[^\s<>"]+token=[^\s<>"]*)',    # URLs with token parameter
    r'(https?://[^\s<>"]+auth[^\s<>"]*)',      # URLs containing "auth"
    r'(https?://[^\s<>"]+validate[^\s<>"]*)',  # URLs containing "validate"
]


@dataclass
class GmailAutomationConfig:
    """Configuration for Gmail automation operations."""
    
    gmail_package: str = GMAIL_PACKAGE
    gmail_activity: str = GMAIL_ACTIVITY
    
    # Polling settings
    poll_interval_seconds: int = 5
    max_wait_seconds: int = 60
    
    # Timeout settings
    element_timeout_seconds: int = 10
    clipboard_timeout_seconds: int = 10
    app_switch_delay_seconds: float = 1.5
    
    # Patterns
    otp_patterns: List[str] = field(default_factory=lambda: OTP_PATTERNS.copy())
    link_patterns: List[str] = field(default_factory=lambda: LINK_PATTERNS.copy())
    
    # Screenshot on failure
    capture_screenshots: bool = True
    screenshot_dir: str = "gmail_failures"


@dataclass
class GmailSearchQuery:
    """Parameters for finding emails in Gmail."""
    
    sender: Optional[str] = None
    sender_contains: Optional[str] = None
    subject_contains: Optional[str] = None
    received_after: Optional[datetime] = None
    is_unread: bool = True
    max_results: int = 5
    
    def to_gmail_query(self) -> str:
        """Convert to Gmail search query string."""
        parts = []
        
        if self.sender:
            parts.append(f"from:{self.sender}")
        elif self.sender_contains:
            parts.append(f"from:{self.sender_contains}")
            
        if self.subject_contains:
            parts.append(f"subject:{self.subject_contains}")
            
        if self.is_unread:
            parts.append("is:unread")
            
        if self.received_after:
            date_str = self.received_after.strftime("%Y/%m/%d")
            parts.append(f"after:{date_str}")
            
        return " ".join(parts)
    
    def is_valid(self) -> bool:
        """Check if at least one search criterion is provided."""
        return any([
            self.sender,
            self.sender_contains,
            self.subject_contains,
            self.received_after,
        ])
