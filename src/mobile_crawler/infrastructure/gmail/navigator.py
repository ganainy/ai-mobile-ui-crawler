"""
Gmail Navigator - Navigate and control the Gmail app on Android.
"""

import time
import subprocess
import logging
from datetime import datetime
from typing import Optional
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from appium.webdriver.common.appiumby import AppiumBy

from .config import (
    GMAIL_PACKAGE,
    GMAIL_ACTIVITY,
    GMAIL_SELECTORS,
    GmailAutomationConfig,
    GmailSearchQuery,
)


logger = logging.getLogger(__name__)


# Error Classes
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


class GmailNavigator:
    """Navigate the Gmail app for email verification workflows."""
    
    def __init__(self, driver, device_id: str, config: Optional[GmailAutomationConfig] = None):
        """
        Initialize Gmail navigator.
        
        Args:
            driver: Appium WebDriver instance
            device_id: Android device ID for ADB commands
            config: Gmail automation configuration
        """
        self.driver = driver
        self.device_id = device_id
        self.config = config or GmailAutomationConfig()
    
    def _run_adb(self, *args) -> subprocess.CompletedProcess:
        """Run an ADB command."""
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    def _save_screenshot(self, name: str):
        """Save screenshot for debugging."""
        if self.config.capture_screenshots:
            try:
                filename = f"{self.config.screenshot_dir}/{name}_{int(time.time())}.png"
                self.driver.save_screenshot(filename)
            except Exception:
                pass
    
    def close_gmail(self):
        """Force stop the Gmail app."""
        self._run_adb('shell', 'am', 'force-stop', GMAIL_PACKAGE)
        time.sleep(0.5)

    def open_gmail(self, force_reset: bool = True) -> bool:
        """
        Launch Gmail app and navigate to inbox.
        
        Args:
            force_reset: If True, force-stops the app before launching to reset UI state
            
        Returns:
            True if Gmail opened and inbox visible, False otherwise
        """
        try:
            if force_reset:
                self.close_gmail()

            # Launch Gmail via ADB
            result = self._run_adb(
                'shell', 'am', 'start', '-n',
                f'{GMAIL_PACKAGE}/{GMAIL_ACTIVITY}'
            )
            
            if result.returncode != 0:
                # Check if Gmail is installed
                check = self._run_adb('shell', 'pm', 'list', 'packages', GMAIL_PACKAGE)
                if GMAIL_PACKAGE not in check.stdout:
                    raise GmailNotInstalledError(f"Gmail app ({GMAIL_PACKAGE}) not installed")
                return False
            
            # Wait for Gmail to load
            time.sleep(self.config.app_switch_delay_seconds)
            
            # Wait for inbox to be visible
            if not self.is_inbox_visible():
                return False

            # Ensure correct account is active
            return self.ensure_correct_account()

            
        except GmailNotInstalledError:
            raise
        except Exception as e:
            self._save_screenshot("gmail_open_failed")
            raise GmailNavigationError(f"Failed to open Gmail: {e}")
    
    def is_inbox_visible(self) -> bool:
        """
        Check if we're currently viewing the inbox.
        
        Returns:
            True if inbox list is visible
        """
        try:
            # Check for sign-in screen
            if self.is_signed_out():
                raise GmailNotSignedInError("Gmail is not signed in to any account")
                
            # Look for language-agnostic resource IDs
            # compose_button ID works regardless of UI language
            WebDriverWait(self.driver, self.config.element_timeout_seconds).until(
                lambda d: (
                    len(d.find_elements(AppiumBy.ID, "com.google.android.gm:id/compose_button")) > 0 or
                    len(d.find_elements(AppiumBy.ID, "com.google.android.gm:id/content_pane")) > 0 or
                    len(d.find_elements(AppiumBy.ID, GMAIL_SELECTORS["recycler_view"])) > 0
                )
            )
            return True
        except GmailNotSignedInError:
            raise
        except TimeoutException:
            return False

    def is_signed_out(self) -> bool:
        """Check if Gmail is on sign-in screen."""
        try:
            # Look for "Add an email address" or "Sign in"
            # Common resource ID for Gmail setup screen
            setup_ids = [
                "com.google.android.gm:id/welcome_tour_got_it",
                "com.google.android.gm:id/setup_addresses_list",
                "com.google.android.gm:id/action_done",
            ]
            for sid in setup_ids:
                if self.driver.find_elements(AppiumBy.ID, sid):
                    return True
            return False
        except:
            return False

    def recover_from_unknown_state(self) -> bool:
        """Attempt to recover Gmail to inbox state."""
        try:
            # 1. Try hitting back a few times
            for _ in range(3):
                self.go_back()
                if self.is_inbox_visible():
                    return True
            
            # 2. Try force-stopping and re-launching
            self._run_adb('shell', 'am', 'force-stop', GMAIL_PACKAGE)
            time.sleep(1)
            return self.open_gmail()
        except:
            return False

    def ensure_correct_account(self) -> bool:
        """
        Verify the active account in Gmail and switch if mismatch with target_account.
        
        Returns:
            True if target account is active or switched successfully
        """
        if not self.config.target_account:
            return True  # No target specified, skip

        logger.info(f"Ensuring Gmail account: {self.config.target_account}")
        try:
            # 1. Check current account using profile ring button
            profile_btn_id = "com.google.android.gm:id/og_apd_ring_view"
            
            try:
                profile_btn = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((AppiumBy.ID, profile_btn_id))
                )
            except TimeoutException:
                # Close any overlay that might be blocking (e.g. search)
                self.recover_from_unknown_state()
                profile_btn = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((AppiumBy.ID, profile_btn_id))
                )

            desc = profile_btn.get_attribute("content-desc") or ""
            
            if self.config.target_account.lower() in desc.lower():
                logger.info(f"Target account {self.config.target_account} is already active.")
                return True
                
            logger.info(f"Account mismatch. Current profile: {desc}. Switching to {self.config.target_account}...")
            
            # 2. Click profile to open account switcher
            profile_btn.click()
            time.sleep(1.5)
            
            # Look for the target account in the list
            # We use an XPath that matches any text view containing the email
            account_xpath = f"//android.widget.TextView[contains(@text, '{self.config.target_account}')]"
            
            try:
                target_item = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((AppiumBy.XPATH, account_xpath))
                )
                target_item.click()
                time.sleep(2)
                
                # Verify switching worked
                profile_btn = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((AppiumBy.ID, profile_btn_id))
                )
                new_desc = profile_btn.get_attribute("content-desc") or ""
                if self.config.target_account.lower() in new_desc.lower():
                    logger.info(f"Successfully switched to {self.config.target_account}")
                    return True
                else:
                    logger.error(f"Failed to confirm switch. Still on: {new_desc}")
                    return False
                    
            except TimeoutException:
                logger.error(f"Target account {self.config.target_account} not found in accounts list.")
                # Try to close switcher
                self.driver.press_keycode(4) # Back
                return False
                
        except Exception as e:
            self._save_screenshot("account_switch_failed")
            logger.error(f"Error during account switching: {e}")
            return False

    
    def refresh_inbox(self) -> bool:
        """
        Refresh the inbox to check for new emails.
        
        Returns:
            True if refresh successful
        """
        try:
            # Swipe down to refresh
            screen_size = self.driver.get_window_size()
            start_x = screen_size['width'] // 2
            start_y = screen_size['height'] // 4
            end_y = screen_size['height'] // 2
            
            # Using ADB swipe for consistency with scroll implementation
            if self.device_id:
                self._run_adb('shell', 'input', 'swipe', str(start_x), str(start_y), str(start_x), str(end_y), '500')
            else:
                if hasattr(self.driver, 'swipe'):
                     self.driver.swipe(start_x, start_y, start_x, end_y, 500)
                else: 
                     pass 

            time.sleep(2)  # Wait for refresh
            return True
        except Exception:
            return False
    
    def open_first_email(self) -> bool:
        """
        Open the first (most recent) email in the current view.
        
        Returns:
            True if email opened, False otherwise
        """
        try:
            # Find first email item
            emails = self.driver.find_elements(AppiumBy.ID, GMAIL_SELECTORS["conversation_item"])
            if not emails:
                # Try finding by subject
                emails = self.driver.find_elements(AppiumBy.ID, GMAIL_SELECTORS["email_subject"])
            
            if not emails:
                raise NoEmailsFoundError("No emails found in inbox")
            
            # Tap first email
            emails[0].click()
            time.sleep(1)
            
            return self.is_email_open()
            
        except NoEmailsFoundError:
            raise
        except Exception as e:
            self._save_screenshot("open_first_email_failed")
            raise GmailNavigationError(f"Failed to open first email: {e}")
    
    def open_email_by_subject(self, subject_contains: str) -> bool:
        """
        Open an email with subject containing the given text.
        
        Args:
            subject_contains: Text to search for in subject
            
        Returns:
            True if email found and opened
        """
        try:
            # Find email by subject text
            xpath = f"//android.widget.TextView[contains(@text, '{subject_contains}')]"
            
            WebDriverWait(self.driver, self.config.element_timeout_seconds).until(
                EC.presence_of_element_located((AppiumBy.XPATH, xpath))
            )
            
            email = self.driver.find_element(AppiumBy.XPATH, xpath)
            email.click()
            time.sleep(1)
            
            return self.is_email_open()
            
        except TimeoutException:
            raise NoEmailsFoundError(f"No email found with subject containing: {subject_contains}")
        except Exception as e:
            self._save_screenshot("open_email_by_subject_failed")
            raise GmailNavigationError(f"Failed to open email by subject: {e}")
    
    def search_emails(self, sender: str = None, subject: str = None, query_obj: GmailSearchQuery = None) -> bool:
        """
        Search for emails matching criteria.
        
        Args:
            sender: Filter by sender email (partial match)
            subject: Filter by subject (partial match)
            query_obj: Pre-built GmailSearchQuery object
            
        Returns:
            True if search executed
        """
        try:
            # Tap search button
            # Look for resource ID first as it's more stable
            search_btn_selectors = [
                (AppiumBy.ID, "com.google.android.gm:id/open_search_bar_text_view"),
                (AppiumBy.ID, "com.google.android.gm:id/open_search_container"),
                (AppiumBy.ACCESSIBILITY_ID, GMAIL_SELECTORS["search_button"])
            ]
            
            search_btn = None
            for by, val in search_btn_selectors:
                try:
                    search_btn = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((by, val))
                    )
                    break
                except:
                    continue
            
            if not search_btn:
                raise GmailNavigationError("Could not find search button")
            
            search_btn.click()
            time.sleep(0.5)
            
            # Build search query
            if query_obj:
                query = query_obj.to_gmail_query()
            else:
                query_parts = []
                if sender:
                    query_parts.append(f"from:{sender}")
                if subject:
                    query_parts.append(f"subject:{subject}")
                query = " ".join(query_parts)
            
            # Enter search query
            search_input = WebDriverWait(self.driver, self.config.element_timeout_seconds).until(
                EC.presence_of_element_located((AppiumBy.CLASS_NAME, GMAIL_SELECTORS["search_input"]))
            )
            search_input.send_keys(query)
            
            # Submit search (press enter)
            self._run_adb('shell', 'input', 'keyevent', '66')
            time.sleep(2)  # Wait for results
            
            return True
            
        except TimeoutException:
            return False
        except Exception as e:
            self._save_screenshot("search_emails_failed")
            raise GmailNavigationError(f"Failed to search emails: {e}")

    def filter_by_timestamp(self, received_after: datetime) -> bool:
        """
        Perform a search for emails received after a specific timestamp.
        
        Args:
            received_after: Datetime object
            
        Returns:
            True if search executed
        """
        query = GmailSearchQuery(received_after=received_after)
        return self.search_emails(query_obj=query)

    
    def go_back(self) -> bool:
        """
        Navigate back (from email to inbox, or exit search).
        
        Returns:
            True if navigation successful
        """
        try:
            # Try tapping back button
            back_btns = self.driver.find_elements(AppiumBy.ACCESSIBILITY_ID, GMAIL_SELECTORS["navigate_up"])
            if back_btns:
                back_btns[0].click()
                time.sleep(0.5)
                return True
            
            # Fallback to hardware back
            self.driver.press_keycode(4)  # KEYCODE_BACK
            time.sleep(0.5)
            return True
            
        except Exception:
            return False
    
    def is_email_open(self) -> bool:
        """
        Check if an email is currently open.
        
        Returns:
            True if viewing email content
        """
        try:
            # Look for webview (HTML email) or subject header
            WebDriverWait(self.driver, 5).until(
                lambda d: (
                    len(d.find_elements(AppiumBy.ID, GMAIL_SELECTORS["webview"])) > 0 or
                    len(d.find_elements(AppiumBy.ID, GMAIL_SELECTORS["subject_header"])) > 0 or
                    len(d.find_elements(AppiumBy.ID, GMAIL_SELECTORS["sender_name"])) > 0
                )
            )
            return True
        except TimeoutException:
            return False
    
    def wait_for_email(
        self,
        sender: str = None,
        subject: str = None,
        timeout: int = None,
        retries_per_refresh: int = 1
    ) -> bool:
        """
        Wait for an email to arrive, polling at regular intervals.
        
        Args:
            sender: Filter by sender (optional)
            subject: Filter by subject (optional)
            timeout: Max wait time in seconds (default from config)
            retries_per_refresh: Number of check attempts after each refresh
            
        Returns:
            True if email found, False on timeout
        """
        timeout = timeout or self.config.max_wait_seconds
        start_time = time.time()
        
        logger.info(f"Waiting for email (sender={sender}, subject={subject}) for up to {timeout}s")
        
        while time.time() - start_time < timeout:
            self.refresh_inbox()
            
            # Check multiple times after refresh if needed
            for _ in range(retries_per_refresh):
                try:
                    if subject:
                        if self.open_email_by_subject(subject):
                            return True
                    elif sender:
                        self.search_emails(sender=sender)
                        if self.open_first_email():
                            return True
                    else:
                        # Just check for any new email
                        if self.open_first_email():
                            return True
                except (NoEmailsFoundError, GmailNavigationError):
                    pass
                
                # Small pause between checks if retrying
                if retries_per_refresh > 1:
                    time.sleep(1)
            
            # Navigate back to inbox if we were in search or email
            if not self.is_inbox_visible():
                self.recover_from_unknown_state()
                
            time.sleep(self.config.poll_interval_seconds)
        
        logger.warning(f"Timeout waiting for email after {timeout}s")
        return False

    
    def clear_search(self) -> bool:
        """Clear the current search and return to inbox."""
        try:
            clear_btns = self.driver.find_elements(
                AppiumBy.ACCESSIBILITY_ID, GMAIL_SELECTORS["clear_search"]
            )
            if clear_btns:
                clear_btns[0].click()
                time.sleep(0.5)
                return True
            
            # Fallback: press back twice
            self.go_back()
            self.go_back()
            return True
        except Exception:
            return False
