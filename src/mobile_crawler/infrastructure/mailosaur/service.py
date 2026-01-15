from typing import Optional

from mailosaur import MailosaurClient
from mailosaur.models import Message, SearchCriteria

from .models import MailosaurConfig


class MailosaurService:
    """Service to interact with Mailosaur API for retrieving emails and SMS."""

    def __init__(self, config: MailosaurConfig):
        """
        Initialize the Mailosaur service.

        Args:
            config: Configuration containing API key and Server ID.
        """
        self.config = config
        self.client = MailosaurClient(self.config.api_key)

    def _get_message(self, criteria: SearchCriteria, timeout: int = 30) -> Message:
        """
        Internal helper to retrieve a message matching criteria within timeout.

        Args:
            criteria: Search criteria to filter messages.
            timeout: Maximum time to wait in seconds.

        Returns:
            The matched Message object.

        Raises:
            MailosaurError: If API interaction fails.
        """
        # Note: mailosaur python sdk `messages.get` handles polling/waiting with timeout
        return self.client.messages.get(self.config.server_id, criteria, timeout=timeout * 1000)

    def get_otp(self, email: str, timeout: int = 30) -> str:
        """
        Retrieves the latest OTP sent to the specified email.
        """
        criteria = SearchCriteria()
        criteria.sent_to = email

        message = self._get_message(criteria, timeout)

        # Try to find code in HTML analysis first
        if message.html and message.html.codes and len(message.html.codes) > 0:
            return message.html.codes[0].value

        # Fallback to text body if no HTML codes found (simplified for now, user specs said extract code)
        if message.text and message.text.codes and len(message.text.codes) > 0:
            return message.text.codes[0].value

        raise ValueError(f"No OTP found in email to {email}")

    def get_magic_link(self, email: str, link_text: Optional[str] = None, timeout: int = 30) -> str:
        """
        Retrieves a verification link (magic link).
        """
        criteria = SearchCriteria()
        criteria.sent_to = email

        message = self._get_message(criteria, timeout)

        # Collect all links from HTML and Text
        all_links = []
        if message.html and message.html.links:
            all_links.extend(message.html.links)
        if message.text and message.text.links:
            all_links.extend(message.text.links)

        if not all_links:
            raise ValueError(f"No magic link found in email to {email}")

        if link_text:
            # Case insensitive match for convenience
            target_text = link_text.lower()
            for link in all_links:
                if link.text and target_text in link.text.lower():
                    return link.href
            raise ValueError(f"No magic link found matching '{link_text}' in email to {email}")

        # Default: return the first link
        return all_links[0].href



