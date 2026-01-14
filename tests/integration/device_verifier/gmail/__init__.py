"""
Gmail automation module for E2E authentication tests.

This module provides utilities for automating Gmail app interactions
to extract OTP codes and click verification links from real emails.

Classes:
    GmailNavigator: Navigate the Gmail app (open, search, select emails)
    GmailReader: Extract OTP codes and verification links from emails
    AppSwitcher: Switch between test app and Gmail reliably
    ClipboardHelper: Clipboard operations for OTP transfer
"""

from .gmail_configs import (
    GmailAutomationConfig,
    GmailSearchQuery,
    GMAIL_PACKAGE,
    GMAIL_ACTIVITY,
    OTP_PATTERNS,
    LINK_PATTERNS,
    GMAIL_SELECTORS,
)
from .gmail_navigator import (
    GmailNavigator,
    GmailNavigationError,
    GmailNotInstalledError,
    NoEmailsFoundError,
)
from .gmail_reader import (
    GmailReader,
    OTPResult,
    LinkResult,
    GmailReadError,
    OTPNotFoundError,
    LinkNotFoundError,
)
from .app_switcher import (
    AppSwitcher,
    AppState,
)
from .clipboard_helper import (
    ClipboardHelper,
)
from .gmail_auth_verifier import GmailAuthVerifier
from .email_sender import EmailSender

__all__ = [
    # Config
    "GmailAutomationConfig",
    "GmailSearchQuery",
    "GMAIL_PACKAGE",
    "GMAIL_ACTIVITY",
    "OTP_PATTERNS",
    "LINK_PATTERNS",
    "GMAIL_SELECTORS",
    # Navigator
    "GmailNavigator",
    "GmailNavigationError",
    "GmailNotInstalledError",
    "NoEmailsFoundError",
    # Reader
    "GmailReader",
    "OTPResult",
    "LinkResult",
    "GmailReadError",
    "OTPNotFoundError",
    "LinkNotFoundError",
    # App Switcher
    "AppSwitcher",
    "AppState",
    # Clipboard
    "ClipboardHelper",
    # Orchestration
    "GmailAuthVerifier",
    # Utility
    "EmailSender",
]
