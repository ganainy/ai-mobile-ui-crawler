from typing import Optional, Protocol
from dataclasses import dataclass

@dataclass
class GmailSearchQuery:
    sender: Optional[str] = None
    subject_contains: Optional[str] = None
    newer_than: str = "1h"

class GmailService(Protocol):
    """
    Interface for Gmail automation service.
    """

    def extract_otp(self, query: GmailSearchQuery, timeout_sec: int = 60) -> Optional[str]:
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
