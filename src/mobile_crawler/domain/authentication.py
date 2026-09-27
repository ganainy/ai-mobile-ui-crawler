"""Authentication as the first Guided Scenario (see CONTEXT.md: App Account, Verification Challenge).

Builds the goal section that tells the agent to sign up or log in, and the agent tools it
uses along the way: "get email code", "get SMS code" and "save app account". The agent has
no tool to voluntarily give up on authentication; failures of the code tools route to Human
Fallback, and a hard cap on code attempts stops the agent from looping on a code that will
never arrive. When that cap (or a declined/timed-out Human Fallback request) makes further
code attempts pointless, the crawl records why and continues on the reachable screens.
"""

import asyncio
import logging
import secrets
import string
from datetime import UTC, datetime
from typing import Any

from mobile_crawler.domain.human_fallback import HumanFallback, RequestKind
from mobile_crawler.infrastructure.app_account_store import AppAccount
from mobile_crawler.infrastructure.sms_reader import SmsReadStatus
from mobile_crawler.infrastructure.verification_inbox import (
    InboxError,
    VerificationInboxConfig,
    default_signup_address,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 3
EMAIL_WAIT_SECONDS = 90.0
SMS_WAIT_SECONDS = 60.0

_GIVE_UP_HINT = "Do not retry this tool again; continue exploring the screens you can reach without finishing sign-in."


_GOOGLE_SIGN_IN_RULE = (
    "GOOGLE SIGN-IN: if the app only offers 'Sign in with Google' / 'Continue with Google' (no email sign-up), "
    "use it with the Google account already on the device: tap the sign-in button, choose the device account "
    "(e.g. 'Continue as <name>') and accept every consent or verification screen from Google Play services "
    "(tap Continue / Allow / Agree / I agree). Never press Back on those Google screens: it cancels the sign-in "
    "and leaves the app. Never abandon the flow while a Google account picker or consent screen is showing; "
    "if a step fails, retry it or restart from the sign-in button rather than giving up. After signing in, "
    "never tap 'Sign out' / 'Log out'."
)


def generate_password() -> str:
    """Random password meeting common complexity rules (upper, lower, digit, symbol)."""
    rng = secrets.SystemRandom()
    chars = [
        rng.choice(string.ascii_uppercase),
        rng.choice(string.ascii_lowercase),
        rng.choice(string.digits),
        rng.choice("!@#$%"),
    ] + [rng.choice(string.ascii_letters + string.digits) for _ in range(8)]
    rng.shuffle(chars)
    return "".join(chars)


class AuthenticationSession:
    """State and agent tools for one run's authentication scenario."""

    def __init__(
        self,
        app_package: str,
        device_id: str,
        account_store,
        inbox_config: VerificationInboxConfig | None,
        inbox_reader,
        sms_reader,
        human_fallback: HumanFallback,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ):
        self.app_package = app_package
        self.device_id = device_id
        self.account_store = account_store
        self.inbox_config = inbox_config
        self.inbox_reader = inbox_reader
        self.sms_reader = sms_reader
        self.human_fallback = human_fallback
        self.max_attempts = max_attempts
        self.attempts = 0
        self.address_override = ""
        self._skipped_reason: str | None = None
        self._started_at = datetime.now(UTC)
        self._signup_password = generate_password()

    @property
    def skipped_reason(self) -> str | None:
        """Why authentication was skipped, or None if it was not."""
        return self._skipped_reason or self.human_fallback.skipped_reason

    # -- goal text -----------------------------------------------------------

    def signup_address(self, account: AppAccount | None = None) -> str | None:
        override = self.address_override or (account.address_override if account else "")
        if override:
            return override
        if self.inbox_config:
            return default_signup_address(self.inbox_config.address, self.app_package)
        return None

    def goal_section(self) -> str:
        """First Guided Scenario: sign up when no App Account exists, otherwise log in."""
        account = self.account_store.get(self.app_package)
        cap = self.max_attempts
        if account:
            return (
                "AUTHENTICATION (do this first): log in with the saved App Account "
                f"(username: {account.username}, password: {account.password}). "
                "If the app logs you out later (you are logged out), log in again with the same account. "
                "Do not create a new account. Email or SMS codes: use get_email_code / get_sms_code "
                f"(at most {cap} code attempts). {_GOOGLE_SIGN_IN_RULE} "
                "Never give up on login voluntarily: keep retrying the sign-in flow and looking for "
                "alternate paths. Only stop once a tool call itself reports the attempt cap is reached, "
                "then continue exploring the reachable screens without a completed login."
            )
        address = self.signup_address()
        if address:
            email_rule = (
                f"Use email address {address} for the email field (the crawler can read its inbox) "
                f"and username {address} if a username is required."
            )
        else:
            email_rule = (
                "No verification inbox is configured: use the form fill email, and if the app "
                "asks for an email code call get_email_code (it will ask the user)."
            )
        return (
            "AUTHENTICATION (do this first): no App Account exists for this app, so sign up. "
            f"{email_rule} Use password {self._signup_password} and the form fill data for other fields. "
            "If the app asks for an emailed code or link, call get_email_code; for an SMS code call get_sms_code "
            f"(at most {cap} code attempts in total). "
            "As soon as sign-up succeeds, call save_app_account with the username and password you used. "
            "These credentials are for a NEW account only: never enter them on a log-in form and never try to "
            "log in (no account exists, so it will fail). If a screen only offers log in, or shows a "
            "wrong email or password error, look for the app's sign-up / create-account option instead. "
            f"{_GOOGLE_SIGN_IN_RULE} "
            "Never give up on sign-up voluntarily: keep retrying and looking for alternate paths "
            "(e.g. a sign-up link on a log-in screen). Only stop once a tool call itself reports the "
            "attempt cap is reached, then continue exploring the reachable screens without an account."
        )

    # -- tools ---------------------------------------------------------------

    def tools(self) -> dict[str, dict[str, Any]]:
        return {
            "get_email_code": {
                "parameters": {},
                "description": (
                    "Get the newest email verification code or link sent to the sign-up address. "
                    "Call after the app says it sent an email. Waits up to about 90 seconds."
                ),
                "function": self._get_email_code,
            },
            "get_sms_code": {
                "parameters": {},
                "description": (
                    "Get the newest SMS verification code received by the device. "
                    "Call after the app says it sent a text message. Waits up to about 60 seconds."
                ),
                "function": self._get_sms_code,
            },
            "save_app_account": {
                "parameters": {
                    "username": {
                        "type": "string",
                        "required": True,
                        "description": "Username or email used to sign up",
                    },
                    "password": {"type": "string", "required": True, "description": "Password used to sign up"},
                },
                "description": "Save the account you just created so the crawler can log in again later.",
                "function": self._save_app_account,
            },
        }

    async def _save_app_account(self, username: str, password: str, ctx=None) -> tuple[bool, str]:
        override = self.address_override
        default = self.signup_address()
        if not override and default and username != default and "@" in username:
            override = username  # the agent used an address other than the plus-addressed default
        self.account_store.save(self.app_package, AppAccount(username, password, override))
        return True, f"Saved App Account {username} for {self.app_package}."

    def _begin_attempt(self) -> tuple[bool, str] | None:
        """Count a code attempt; return a failure result once the cap is reached."""
        if self.attempts >= self.max_attempts:
            self._skipped_reason = self._skipped_reason or (
                f"authentication skipped: attempt cap of {self.max_attempts} reached"
            )
            return False, f"Authentication attempt cap ({self.max_attempts}) reached. {_GIVE_UP_HINT}"
        self.attempts += 1
        return None

    async def _get_email_code(self, ctx=None) -> tuple[bool, str]:
        if (blocked := self._begin_attempt()) is not None:
            return blocked
        address = self.signup_address(self.account_store.get(self.app_package))
        problem = "no Verification Inbox configured"
        if self.inbox_reader is not None and address:
            try:
                result = await asyncio.to_thread(
                    self.inbox_reader.wait_for_verification, address, self._started_at, EMAIL_WAIT_SECONDS
                )
                parts = []
                if result.code:
                    parts.append(f"Email code: {result.code}")
                if result.link:
                    parts.append(f"Verification link: {result.link} (open it in the device browser or the app)")
                return True, ". ".join(parts) or "Email arrived but contained no code or link."
            except InboxError as e:
                problem = str(e)
        return await self._ask_human(
            f"Enter the email verification code sent to {address or 'the sign-up address'}", problem
        )

    async def _get_sms_code(self, ctx=None) -> tuple[bool, str]:
        if (blocked := self._begin_attempt()) is not None:
            return blocked
        problem = "no SMS reader available"
        if self.sms_reader is not None:
            result = await self.sms_reader.read_otp(self.device_id, timeout_seconds=SMS_WAIT_SECONDS)
            if result.status is SmsReadStatus.FOUND:
                return True, f"SMS code: {result.code}"
            problem = result.message or result.status.value
        return await self._ask_human("Enter the SMS verification code received on the device", problem)

    async def _ask_human(self, message: str, problem: str) -> tuple[bool, str]:
        logger.info("Verification code lookup failed (%s); using Human Fallback", problem)
        outcome = await asyncio.to_thread(
            self.human_fallback.request, RequestKind.CODE, f"{message}. (Automatic lookup failed: {problem})"
        )
        if outcome.answered and outcome.code:
            return True, f"Code from user: {outcome.code}"
        return False, f"Could not get a code ({outcome.skip_note or problem}). {_GIVE_UP_HINT}"
