"""
Email Sender - Utility to send authentication emails for testing.
This mimics the backend behavior for apps that don't have a real mailer.
"""

import smtplib
import ssl
import os
import logging
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)

class EmailSender:
    """Sends authentication emails via SMTP."""
    
    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 465,
        sender_email: str = "afoda50@gmail.com"
    ):
        """
        Initialize the email sender.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP port (default 465 for SSL)
            sender_email: The email address sending the mail
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        
        # Get password from environment variable
        self.app_password = os.environ.get("GMAIL_TEST_APP_PASSWORD")
        
        # Fallback to .env file if available
        if not self.app_password:
            try:
                # Look for .env in project root (assuming E:\VS-projects\mobile-crawler)
                env_path = os.path.join(os.getcwd(), ".env")
                if os.path.exists(env_path):
                    with open(env_path, "r") as f:
                        for line in f:
                            if line.startswith("GMAIL_TEST_APP_PASSWORD="):
                                self.app_password = line.split("=", 1)[1].strip()
                                break
            except Exception as e:
                logger.warning(f"Failed to read .env file: {e}")

    def send_otp_email(
        self, 
        recipient_email: str, 
        otp: str = "123456",
        subject: str = "Verification"
    ) -> bool:
        """
        Send an OTP verification email.
        
        Args:
            recipient_email: Who to send the email to
            otp: The 6-digit code
            subject: The email subject
            
        Returns:
            True if sent successfully
        """
        if not self.app_password:
            msg = "GMAIL_TEST_APP_PASSWORD not set in environment. Cannot send test email."
            logger.error(msg)
            raise ValueError(msg)
            
        msg = EmailMessage()
        msg.set_content(f"Your verification code is: {otp}")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = recipient_email
        
        return self._send(msg)

    def send_link_email(
        self,
        recipient_email: str,
        token: str = "TESTTOKEN",
        subject: str = "Verify"
    ) -> bool:
        """
        Send a verification link email.
        
        Args:
            recipient_email: Who to send the email to
            token: The verification token
            subject: The email subject
            
        Returns:
            True if sent successfully
        """
        if not self.app_password:
            msg = "GMAIL_TEST_APP_PASSWORD not set in environment. Cannot send test email."
            logger.error(msg)
            raise ValueError(msg)
            
        # Using the testapp scheme defined in TestConstants
        link = f"testapp://verify?token={token}"
        
        msg = EmailMessage()
        msg.set_content(f"Click the link to verify: {link}")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = recipient_email
        
        return self._send(msg)

    def _send(self, msg: EmailMessage) -> bool:
        """Internal method to handle the SMTP connection."""
        context = ssl.create_default_context()
        
        try:
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                server.login(self.sender_email, self.app_password)
                server.send_message(msg)
            logger.info(f"Email sent successfully to {msg['To']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
