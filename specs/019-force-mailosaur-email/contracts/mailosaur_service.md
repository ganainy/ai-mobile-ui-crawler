# Contract: MailosaurService

**Feature**: 019-force-mailosaur-email  
**Date**: 2026-01-15

## Service Interface

```python
from typing import Optional
from dataclasses import dataclass


@dataclass
class MailosaurConfig:
    """Configuration for Mailosaur service."""
    api_key: str
    server_id: str


class MailosaurService:
    """Service to interact with Mailosaur API for retrieving emails."""

    def __init__(self, config: MailosaurConfig):
        """
        Initialize the Mailosaur service.

        Args:
            config: Configuration containing API key and Server ID.
        
        Raises:
            ValueError: If config is invalid (missing API key or server ID)
        """
        pass

    def get_otp(self, email: str, timeout: int = 30) -> str:
        """
        Retrieve the latest OTP sent to the specified email.

        Args:
            email: The email address to search for messages
            timeout: Maximum time to wait for a message (seconds)

        Returns:
            The extracted OTP code as a string

        Raises:
            ValueError: If no OTP found in the message
            MailosaurError: If API interaction fails
            TimeoutError: If no message arrives within timeout
        """
        pass

    def get_magic_link(
        self, 
        email: str, 
        link_text: Optional[str] = None, 
        timeout: int = 30
    ) -> str:
        """
        Retrieve a verification link (magic link) from the latest email.

        Args:
            email: The email address to search for messages
            link_text: Optional anchor text to match specific link
            timeout: Maximum time to wait for a message (seconds)

        Returns:
            The extracted verification URL

        Raises:
            ValueError: If no matching link found in the message
            MailosaurError: If API interaction fails
            TimeoutError: If no message arrives within timeout
        """
        pass
```

## Usage Example

```python
from mobile_crawler.infrastructure.mailosaur.service import MailosaurService
from mobile_crawler.infrastructure.mailosaur.models import MailosaurConfig

# Initialize service
config = MailosaurConfig(
    api_key="your-api-key",
    server_id="abc12345"
)
service = MailosaurService(config)

# Extract OTP
try:
    otp = service.get_otp(
        email="user@abc12345.mailosaur.net",
        timeout=60
    )
    print(f"OTP: {otp}")
except ValueError as e:
    print(f"OTP not found: {e}")

# Extract magic link
try:
    link = service.get_magic_link(
        email="user@abc12345.mailosaur.net",
        link_text="Verify Email",  # Optional
        timeout=60
    )
    print(f"Verification URL: {link}")
except ValueError as e:
    print(f"Link not found: {e}")
```

## Integration Points

### ActionExecutor

The `ActionExecutor` class uses `MailosaurService` for email verification:

```python
class ActionExecutor:
    def __init__(
        self, 
        appium_driver: AppiumDriver, 
        gesture_handler: GestureHandler,
        adb_input_handler: Optional[ADBInputHandler] = None,
        mailosaur_service: Optional[MailosaurService] = None
    ):
        self.mailosaur_service = mailosaur_service
        # ...

    def extract_otp(
        self, 
        email: str,
        timeout: int = 60
    ) -> ActionResult:
        """Execute OTP extraction from Mailosaur."""
        if not self.mailosaur_service:
            return ActionResult(
                success=False, 
                error_message="Mailosaur service not configured"
            )
        
        try:
            otp = self.mailosaur_service.get_otp(email, timeout)
            return ActionResult(
                success=True,
                action_type="extract_otp",
                input_text=otp
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="extract_otp",
                error_message=str(e)
            )
```

### MainWindow Service Initialization

```python
# In _create_crawler_loop():
from mobile_crawler.infrastructure.mailosaur.service import MailosaurService
from mobile_crawler.infrastructure.mailosaur.models import MailosaurConfig

# Get config from environment or settings
api_key = os.environ.get('MAILOSAUR_API_KEY') or config_manager.get('mailosaur_api_key')
server_id = os.environ.get('MAILOSAUR_SERVER_ID') or config_manager.get('mailosaur_server_id')

if api_key and server_id:
    mailosaur_config = MailosaurConfig(api_key=api_key, server_id=server_id)
    mailosaur_service = MailosaurService(mailosaur_config)
else:
    mailosaur_service = None  # Service unavailable

action_executor = ActionExecutor(
    appium_driver, 
    gesture_handler, 
    mailosaur_service=mailosaur_service
)
```
