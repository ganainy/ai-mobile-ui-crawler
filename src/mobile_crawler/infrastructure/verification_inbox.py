"""Verification Inbox: read email codes and links from Gmail over IMAP (see CONTEXT.md).

Standalone: no agent dependency. The address is stored in plain settings and the
app password encrypted in the secrets table, like an App Account.
"""

import email
import imaplib
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import Message
from email.utils import parsedate_to_datetime

from mobile_crawler.infrastructure.user_config_store import UserConfigStore

IMAP_HOST = "imap.gmail.com"
POLL_INTERVAL_SECONDS = 5.0
INBOX_ADDRESS_KEY = "verification_inbox_address"
INBOX_PASSWORD_KEY = "verification_inbox_password"

_CODE_RE = re.compile(r"(?<![\w.])(\d{4,8})(?!\w)(?!\.\d)")
_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
_HREF_RE = re.compile(r'href="([^"]+)"')
_TAG_RE = re.compile(r"<[^>]+>")
_LINK_HINTS = ("verify", "confirm", "activate", "token", "code", "auth", "validate")


class InboxError(Exception):
    """Base class for Verification Inbox failures."""


class InboxAuthError(InboxError):
    """Gmail rejected the login or IMAP is disabled."""


class InboxConnectionError(InboxError):
    """Could not reach the IMAP server."""


class InboxTimeoutError(InboxError):
    """No matching message arrived within the timeout."""


@dataclass(frozen=True)
class VerificationInboxConfig:
    address: str
    app_password: str


@dataclass(frozen=True)
class VerificationResult:
    """Newest verification message content: a code, a link, or both."""

    code: str | None
    link: str | None
    received_at: datetime


def default_signup_address(inbox_address: str, app_package: str) -> str:
    """Plus-addressed sign-up email, e.g. `name+com.foo.app@gmail.com`."""
    local, _, domain = inbox_address.partition("@")
    return f"{local}+{app_package}@{domain}"


def extract_code(text: str) -> str | None:
    """First 4-8 digit code that isn't a plausible year."""
    for match in _CODE_RE.finditer(text):
        value = match.group(1)
        if len(value) == 4 and 1900 <= int(value) <= 2100:
            continue
        return value
    return None


def extract_link(text: str) -> str | None:
    """First URL that looks like a verification link, else None."""
    for url in (u.rstrip(".,;") for u in _URL_RE.findall(text)):
        if any(hint in url.lower() for hint in _LINK_HINTS):
            return url
    return None


def _message_text(msg: Message) -> str:
    parts: list[str] = []
    for part in msg.walk():
        if part.get_content_maintype() != "text":
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if part.get_content_subtype() == "html":
            text = _TAG_RE.sub(" ", text) + "\n" + "\n".join(_HREF_RE.findall(text))
        parts.append(text)
    return "\n".join(parts)


def _to_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


class VerificationInboxReader:
    """Polls Gmail over IMAP for the newest verification code or link sent to an address."""

    def __init__(
        self,
        address: str,
        app_password: str,
        imap_factory: Callable[[], imaplib.IMAP4] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self._address = address
        self._password = app_password
        self._imap_factory = imap_factory or (lambda: imaplib.IMAP4_SSL(IMAP_HOST))
        self._sleep = sleep
        self._monotonic = monotonic

    def wait_for_verification(
        self, recipient: str, since: datetime, timeout_seconds: float
    ) -> VerificationResult:
        """Return the newest code/link sent to `recipient` at or after `since`.

        Raises InboxAuthError, InboxConnectionError or InboxTimeoutError.
        """
        since = _to_utc(since)
        deadline = self._monotonic() + timeout_seconds
        imap = self._connect()
        try:
            while True:
                result = self._find(imap, recipient, since)
                if result is not None:
                    return result
                if self._monotonic() >= deadline:
                    raise InboxTimeoutError(
                        f"No verification email for {recipient} arrived within {timeout_seconds:g}s."
                    )
                self._sleep(POLL_INTERVAL_SECONDS)
        finally:
            try:
                imap.logout()
            except Exception:
                pass

    def _connect(self) -> imaplib.IMAP4:
        try:
            imap = self._imap_factory()
        except OSError as exc:
            raise InboxConnectionError(f"Could not connect to {IMAP_HOST}: {exc}") from exc
        try:
            imap.login(self._address, self._password)
        except imaplib.IMAP4.error as exc:
            first = exc.args[0] if exc.args else ""
            text = first.decode(errors="replace") if isinstance(first, bytes) else str(first)
            if "disabled" in text.lower():
                raise InboxAuthError(
                    "IMAP is disabled for this Gmail account. Enable it in Gmail settings > Forwarding and POP/IMAP."
                ) from exc
            raise InboxAuthError(
                "Gmail rejected the login. Check the address and use an app password "
                "(needs 2-Step Verification), not the account password."
            ) from exc
        except OSError as exc:
            raise InboxConnectionError(f"Connection to {IMAP_HOST} failed: {exc}") from exc
        return imap

    def _find(self, imap: imaplib.IMAP4, recipient: str, since: datetime) -> VerificationResult | None:
        candidates: list[VerificationResult] = []
        try:
            imap.select("INBOX", readonly=True)
            status, data = imap.search(None, "TO", f'"{recipient}"', "SINCE", since.strftime("%d-%b-%Y"))
            if status != "OK":
                return None
            for uid in data[0].split() if data and data[0] else []:
                status, msg_data = imap.fetch(uid, "(RFC822)")
                if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                try:
                    received = _to_utc(parsedate_to_datetime(msg["Date"]))
                except (TypeError, ValueError):
                    continue
                if received < since:
                    continue
                text = _message_text(msg)
                code, link = extract_code(text), extract_link(text)
                if code or link:
                    candidates.append(VerificationResult(code, link, received))
        except OSError as exc:
            raise InboxConnectionError(f"Lost connection to {IMAP_HOST}: {exc}") from exc
        return max(candidates, key=lambda r: r.received_at) if candidates else None


class VerificationInboxStore:
    """Reads and writes the Verification Inbox credentials."""

    def __init__(self, user_config_store: UserConfigStore):
        self._store = user_config_store

    def get(self) -> VerificationInboxConfig | None:
        address = self._store.get_setting(INBOX_ADDRESS_KEY)
        if not address:
            return None
        password = self._store.get_secret_plaintext(INBOX_PASSWORD_KEY) or ""
        return VerificationInboxConfig(str(address), password)

    def save(self, config: VerificationInboxConfig) -> None:
        self._store.set_setting(INBOX_ADDRESS_KEY, config.address, "string")
        if config.app_password:
            self._store.set_secret_plaintext(INBOX_PASSWORD_KEY, config.app_password)
        else:
            self._store.delete_secret(INBOX_PASSWORD_KEY)

    def delete(self) -> None:
        self._store.delete_setting(INBOX_ADDRESS_KEY)
        self._store.delete_secret(INBOX_PASSWORD_KEY)
