import os
import time
import uuid
import smtplib
import ssl
from email.message import EmailMessage
import pytest
from mobile_crawler.infrastructure.mailosaur import MailosaurService, MailosaurConfig

# Credentials (from user request and .env)
API_KEY = "RfhEdaccBJvApWJ4HmCt7G5sZGFdjyg4"
SERVER_ID = "bfovcwfh"
SENDER_EMAIL = "afoda50@gmail.com"
# GMAIL_TEST_APP_PASSWORD will be read from .env

class SimpleEmailSender:
    """Standalone sender to avoids broken package imports."""
    def __init__(self):
        self.app_password = os.environ.get("GMAIL_TEST_APP_PASSWORD")
        if not self.app_password:
            # Try reading .env manually
            if os.path.exists(".env"):
                with open(".env", "r") as f:
                    for line in f:
                        if line.startswith("GMAIL_TEST_APP_PASSWORD="):
                            self.app_password = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
                            
    def send(self, to, subject, body):
        if not self.app_password:
            raise ValueError("GMAIL_TEST_APP_PASSWORD not found")
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to
        
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, self.app_password)
            server.send_message(msg)
        return True

@pytest.fixture
def mailosaur_service():
    config = MailosaurConfig(api_key=API_KEY, server_id=SERVER_ID)
    return MailosaurService(config)

@pytest.fixture
def email_sender():
    return SimpleEmailSender()

def test_live_otp_flow(mailosaur_service, email_sender):
    """Test OTP: Send via Gmail, Receive via Mailosaur."""
    otp = str(uuid.uuid4().int)[:6]
    recipient = f"otp-{uuid.uuid4().hex[:8]}@{SERVER_ID}.mailosaur.net"
    
    print(f"\n[OTP] Sending {otp} to {recipient}...")
    email_sender.send(recipient, "Verify your account", f"Your code is {otp}")
    
    print("[OTP] Waiting for Mailosaur...")
    received = mailosaur_service.get_otp(recipient, timeout=60)
    print(f"[OTP] Success: Got {received}")
    assert received == otp

def test_live_magic_link_flow(mailosaur_service, email_sender):
    """Test Magic Link: Send via Gmail, Receive via Mailosaur."""
    token = uuid.uuid4().hex
    recipient = f"link-{uuid.uuid4().hex[:8]}@{SERVER_ID}.mailosaur.net"
    link = f"https://example.com/verify?token={token}"
    
    print(f"\n[Link] Sending link to {recipient}...")
    email_sender.send(recipient, "Sign in to App", f"Click here to verify: {link}")
    
    print("[Link] Waiting for Mailosaur...")
    # The default get_magic_link returns the first link found
    received_link = mailosaur_service.get_magic_link(recipient, timeout=60)
    print(f"[Link] Success: Got {received_link}")
    assert token in received_link



