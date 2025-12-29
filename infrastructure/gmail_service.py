
import imaplib
import email
import re
import time
import logging
from email.header import decode_header
import datetime

logger = logging.getLogger(__name__)

class GmailService:
    """
    Service to interact with Gmail via IMAP to fetch verification codes.
    """

    def __init__(self, user: str, password: str, imap_url: str = 'imap.gmail.com'):
        self.user = user
        self.password = password
        self.imap_url = imap_url

    def fetch_latest_email_content(self, timeout: int = 60, min_timestamp: float = None) -> tuple[str, str]:
        """
        Fetches the latest verification code from recent emails.
        
        Args:
            timeout: Max time to wait/search in seconds.
            min_timestamp: Unix timestamp (float). Emails older than this will be ignored. Should be set to when the OTP was requested.
            
        Returns:
            Tuple of (subject, body), or ("", "") if not found.
        """
        if not self.user or not self.password:
            logger.error("Gmail credentials not provided.")
            return ""

        mail = None
        start_time = time.time()
        end_time = start_time + timeout
        poll_interval = 5  # Seconds between checks

        logger.info(f"Starting Gmail OTP search for user {self.user} (Timeout: {timeout}s)")

        while time.time() < end_time:
            try:
                # Re-connect/Select inbox on each iteration to ensure we see new messages
                if mail:
                    try:
                        mail.close()  # Close selection
                        mail.logout() # Logout to be clean
                    except:
                        pass
                
                # Connect to Gmail (fresh connection each time to avoid state issues)
                mail = imaplib.IMAP4_SSL(self.imap_url)
                mail.login(self.user, self.password)
                mail.select("inbox")

                # SEARCH ALL and slice locally - safer than relying on SINCE date logic which can fail with timezones
                status, messages = mail.search(None, "ALL")
                
                if status != "OK":
                    logger.debug("No messages found in search (IMAP status not OK).")
                    time.sleep(poll_interval)
                    continue

                email_ids = messages[0].split()
                if not email_ids:
                     logger.debug("Inbox is empty.")
                     time.sleep(poll_interval)
                     continue
                logger.info(f"Found {len(email_ids)} messages in inbox. Checking the VERY LAST email.")
                
                # Check ONLY the last message as requested
                recent_ids = [email_ids[-1]]
                
                # Process most recent first
                for email_id in reversed(recent_ids):
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # Log everything about this email
                            subject_header = decode_header(msg["Subject"])[0]
                            subject = subject_header[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(subject_header[1] if subject_header[1] else "utf-8")
                                
                            email_date_raw = msg["Date"]
                            email_date = email.utils.parsedate_to_datetime(email_date_raw)
                            
                            logger.info(f"INSPECTING EMAIL: Subject='{subject}' | Date='{email_date_raw}'")

                            # Check timestamp (Soft check - only warn)
                            if email_date and min_timestamp:
                                email_ts = email_date.timestamp()
                                # Allow 2 minutes drift/delay grace period
                                if email_ts < (min_timestamp - 120):
                                    logger.warning(f"  -> WARNING: Email is older than requested window (Ts: {email_ts} < Min: {min_timestamp}). Proceeding anyway as requested.")
                            
                            # Extract body
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    if content_type == "text/plain": # Prefer plain text
                                        try:
                                            body = part.get_payload(decode=True).decode()
                                            break # Found plain text, stop
                                        except:
                                            pass
                                    elif content_type == "text/html" and not body: # Fallback to HTML if no plain text yet
                                        try:
                                            body = part.get_payload(decode=True).decode()
                                            # Clean HTML tags roughly for the AI
                                            body = re.sub(r'<[^>]+>', '', body)
                                        except:
                                            pass
                            else:
                                body = msg.get_payload(decode=True).decode()
                                if msg.get_content_type() == "text/html":
                                      body = re.sub(r'<[^>]+>', '', body)

                            logger.info(f"  -> Returned email content for AI extraction.")
                            return subject, body

                # If we get here, no email found in this pass (or empty inbox)
                remaining = int(end_time - time.time())
                if remaining > 0:
                    logger.info(f"Email not found yet. Retrying in {poll_interval}s... ({remaining}s remaining)")
                    time.sleep(poll_interval)
                
            except Exception as e:
                logger.warning(f"Error during polling attempt: {e}")
                # Wait before retry if error occurred
                time.sleep(poll_interval)

        logger.info("Timeout reached. No email found.")
        return "", ""


