# Gmail Navigator Contract

**Module**: `tests/integration/device_verifier/gmail/gmail_navigator.py`
**Purpose**: Navigate and control the Gmail app on an Android device

## Interface

```python
class GmailNavigator:
    """Navigate the Gmail app for email verification workflows."""
    
    def __init__(self, driver, device_id: str):
        """
        Initialize Gmail navigator.
        
        Args:
            driver: Appium WebDriver instance
            device_id: Android device ID for ADB commands
        """
        pass
    
    def open_gmail(self) -> bool:
        """
        Launch Gmail app and navigate to inbox.
        
        Returns:
            True if Gmail opened and inbox visible, False otherwise
            
        Side Effects:
            - Switches active app to Gmail
            - May take 2-3 seconds for app to load
        """
        pass
    
    def refresh_inbox(self) -> bool:
        """
        Refresh the inbox to check for new emails.
        
        Returns:
            True if refresh successful, False otherwise
        """
        pass
    
    def search_emails(self, sender: str = None, subject: str = None) -> bool:
        """
        Search for emails matching criteria.
        
        Args:
            sender: Filter by sender email (partial match)
            subject: Filter by subject (partial match)
            
        Returns:
            True if search executed, False otherwise
            
        Note:
            At least one criterion must be provided
        """
        pass
    
    def open_first_email(self) -> bool:
        """
        Open the first (most recent) email in the current view.
        
        Returns:
            True if email opened, False otherwise
            
        Raises:
            NoEmailsFoundError: If no emails in current view
        """
        pass
    
    def open_email_by_subject(self, subject_contains: str) -> bool:
        """
        Open an email with subject containing the given text.
        
        Args:
            subject_contains: Text to search for in subject
            
        Returns:
            True if email found and opened, False otherwise
        """
        pass
    
    def go_back(self) -> bool:
        """
        Navigate back (from email to inbox, or exit search).
        
        Returns:
            True if navigation successful
        """
        pass
    
    def is_inbox_visible(self) -> bool:
        """
        Check if we're currently viewing the inbox.
        
        Returns:
            True if inbox list is visible
        """
        pass
    
    def is_email_open(self) -> bool:
        """
        Check if an email is currently open.
        
        Returns:
            True if viewing email content
        """
        pass
```

## Error Types

```python
class GmailNavigationError(Exception):
    """Base error for Gmail navigation failures."""
    pass

class GmailNotInstalledError(GmailNavigationError):
    """Gmail app not installed on device."""
    pass

class GmailNotSignedInError(GmailNavigationError):
    """Gmail app not signed in to any account."""
    pass

class NoEmailsFoundError(GmailNavigationError):
    """No emails matching search criteria."""
    pass
```

## Constants

```python
GMAIL_PACKAGE = "com.google.android.gm"
GMAIL_ACTIVITY = "com.google.android.gm.ConversationListActivityGmail"

SELECTORS = {
    "inbox_list": "com.google.android.gm:id/conversation_list",
    "email_subject": "com.google.android.gm:id/subject",
    "email_sender": "com.google.android.gm:id/senders", 
    "search_button": "Search in mail",
    "search_input": "android.widget.EditText",
    "navigate_up": "Navigate up",
}
```

## Usage Example

```python
gmail = GmailNavigator(driver, device_id)

# Open Gmail and wait for inbox
assert gmail.open_gmail(), "Failed to open Gmail"

# Search for verification email
gmail.search_emails(sender="noreply@example.com", subject="Verify")

# Open the email
assert gmail.open_first_email(), "No verification email found"

# (Use GmailReader to extract content)
```
