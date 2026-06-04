from dataclasses import dataclass
from typing import Protocol


@dataclass
class GmailSearchQuery:
    sender: str | None = None
    subject_contains: str | None = None
    newer_than: str = "1h"

class GmailService(Protocol):
    """
    Interface for Gmail automation service.
    """

    def extract_otp(self, query: GmailSearchQuery, timeout_sec: int = 60) -> str | None:
        """
        Switch to Gmail, find the email matching the query, extract the OTP,
        switch back to the original app, and return the OTP.

        Args:
            query: Search criteria for the email.
            timeout_sec: Max time to wait for email.

        Returns:
            The extracted OTP string, or None if not found/timed out.
        """
        ...

    def click_verification_link(self, query: GmailSearchQuery, timeout_sec: int = 60) -> bool:
        """
        Switch to Gmail, find the email matching the query, click the verification link,
        wait for the redirect/app switch, and return success status.

        Args:
            query: Search criteria for the email.
            timeout_sec: Max time to wait for email.

        Returns:
            True if link found and clicked, False otherwise.
        """
        ...
