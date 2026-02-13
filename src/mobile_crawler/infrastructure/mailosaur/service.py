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

        # Strategy: Use scoring to pick the best link
        scored_links = []
        
        # Keywords to look for
        action_keywords = ["verify", "confirm", "bestätigen", "activate", "continue", "click here", "registration", "anmeldung"]
        path_keywords = ["/verify", "/confirm", "/activate", "/registration", "/auth", "/token", "/link"]
        exclude_keywords = ["logo", "unsubscribe", "privacy", "terms", "datenschutz", "impressum", "facebook", "twitter", "instagram"]

        for link in all_links:
            score = 0
            href = (link.href or "").lower()
            text = (link.text or "").lower()

            # 1. Check Link Text
            if text:
                if any(k in text for k in action_keywords):
                    score += 10
                if any(k in text for k in exclude_keywords):
                    score -= 15
            
            # 2. Check URL Path
            if any(k in href for k in path_keywords):
                score += 15
            if any(k in href for k in exclude_keywords):
                score -= 15
            
            # 3. Signals (Length implies token)
            if len(href) > 60:
                score += 5
            
            # 4. Exclude static assets/root domains
            if href.split("?")[0].endswith((".png", ".jpg", ".jpeg", ".gif")):
                score -= 30
            
            scored_links.append((score, link))

        # Sort by score descending
        scored_links.sort(key=lambda x: x[0], reverse=True)
        
        # Log top links for debugging
        import logging
        logger = logging.getLogger(__name__)
        for s, l in scored_links[:3]:
            logger.debug(f"Candidate Link: Score={s}, Text='{l.text}', Href='{l.href[:50]}...'")

        if link_text:
            # If AI provided a specific hint, try to match it first
            target_text = link_text.lower()
            for score, link in scored_links:
                if link.text and target_text in link.text.lower():
                    return link.href
            # Fallback to the highest scoring link if AI hint didn't match anything
            logger.warning(f"AI hint '{link_text}' did not match any links, falling back to highest score")

        # Return the link with the highest score
        return scored_links[0][1].href



