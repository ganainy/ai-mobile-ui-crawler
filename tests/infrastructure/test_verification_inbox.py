"""Tests for the Gmail IMAP Verification Inbox reader."""

import imaplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime

import pytest

from mobile_crawler.infrastructure.user_config_store import UserConfigStore
from mobile_crawler.infrastructure.verification_inbox import (
    InboxAuthError,
    InboxConnectionError,
    InboxTimeoutError,
    VerificationInboxConfig,
    VerificationInboxReader,
    VerificationInboxStore,
    default_signup_address,
    extract_code,
    extract_link,
)

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)


def _mail(to: str, body: str, sent: datetime = NOW, html: str | None = None) -> bytes:
    msg = EmailMessage()
    msg["To"] = to
    msg["From"] = "noreply@app.example"
    msg["Subject"] = "Verify"
    msg["Date"] = format_datetime(sent)
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    return msg.as_bytes()


class FakeImap:
    """Minimal imaplib.IMAP4_SSL stand-in holding {uid: raw_message}."""

    def __init__(self, messages: dict[bytes, bytes], login_error: Exception | None = None):
        self.messages = messages
        self.login_error = login_error
        self.searches: list[tuple] = []
        self.logged_out = False

    def login(self, user, password):
        if self.login_error:
            raise self.login_error
        return "OK", [b"logged in"]

    def select(self, mailbox, readonly=False):
        return "OK", [b"1"]

    def search(self, charset, *criteria):
        self.searches.append(criteria)
        return "OK", [b" ".join(self.messages)]

    def fetch(self, uid, spec):
        return "OK", [(b"1 (RFC822 {1})", self.messages[uid])]

    def logout(self):
        self.logged_out = True
        return "BYE", []


def _reader(fake, sleeps=None):
    clock = [0.0]

    def monotonic():
        clock[0] += 10
        return clock[0]

    return VerificationInboxReader(
        "me@gmail.com",
        "app-pass",
        imap_factory=lambda: fake,
        sleep=(sleeps.append if sleeps is not None else (lambda s: None)),
        monotonic=monotonic,
    )


def test_default_signup_address_is_plus_addressed():
    assert default_signup_address("me@gmail.com", "com.foo.app") == "me+com.foo.app@gmail.com"


def test_extract_code_finds_six_digit_code():
    assert extract_code("Your verification code is 482913. It expires soon.") == "482913"


def test_extract_code_ignores_years_and_returns_none_when_absent():
    assert extract_code("Welcome to 2026! No code here.") is None


def test_extract_link_prefers_verification_like_url():
    body = "Visit https://app.example/home or confirm at https://app.example/verify?token=abc123 now."
    assert extract_link(body) == "https://app.example/verify?token=abc123"


def test_extract_link_none_when_no_url():
    assert extract_link("nothing here") is None


def test_wait_returns_code_from_newest_message_to_recipient():
    to = "me+com.foo@gmail.com"
    fake = FakeImap({
        b"1": _mail(to, "Code 111111", NOW),
        b"2": _mail(to, "Code 222222", NOW + timedelta(minutes=1)),
    })
    result = _reader(fake).wait_for_verification(to, since=NOW - timedelta(minutes=1), timeout_seconds=60)
    assert result.code == "222222"
    assert fake.logged_out
    assert any(to in str(c) for c in fake.searches[0])


def test_wait_returns_link_when_only_link_present():
    to = "me+x@gmail.com"
    fake = FakeImap({b"1": _mail(to, "Confirm: https://app.example/confirm?t=9")})
    result = _reader(fake).wait_for_verification(to, since=NOW - timedelta(minutes=1), timeout_seconds=60)
    assert result.link == "https://app.example/confirm?t=9"
    assert result.code is None


def test_wait_reads_html_only_part():
    to = "me+x@gmail.com"
    raw = _mail(to, "Your code is below.", html="<p>Your code: <b>654321</b></p>")
    fake = FakeImap({b"1": raw})
    result = _reader(fake).wait_for_verification(to, since=NOW - timedelta(minutes=1), timeout_seconds=60)
    assert result.code == "654321"


def test_messages_older_than_window_are_ignored_then_times_out():
    to = "me+x@gmail.com"
    fake = FakeImap({b"1": _mail(to, "Code 123456", NOW - timedelta(hours=1))})
    sleeps: list[float] = []
    with pytest.raises(InboxTimeoutError):
        _reader(fake, sleeps=sleeps).wait_for_verification(to, since=NOW, timeout_seconds=30)
    assert sleeps  # polled more than once


def test_bad_credentials_raise_auth_error():
    fake = FakeImap({}, login_error=imaplib.IMAP4.error(b"[AUTHENTICATIONFAILED] Invalid credentials"))
    with pytest.raises(InboxAuthError, match="app password"):
        _reader(fake).wait_for_verification("a@b.c", since=NOW, timeout_seconds=5)


def test_imap_disabled_message_is_clear():
    fake = FakeImap({}, login_error=imaplib.IMAP4.error(b"[ALERT] IMAP access is disabled for your account"))
    with pytest.raises(InboxAuthError, match="IMAP is disabled"):
        _reader(fake).wait_for_verification("a@b.c", since=NOW, timeout_seconds=5)


def test_network_failure_raises_connection_error():
    def boom():
        raise OSError("no route")

    reader = VerificationInboxReader("me@gmail.com", "pw", imap_factory=boom)
    with pytest.raises(InboxConnectionError):
        reader.wait_for_verification("a@b.c", since=NOW, timeout_seconds=5)


def test_store_roundtrips_config_with_encrypted_password(tmp_path):
    ucs = UserConfigStore(tmp_path / "c.db")
    ucs.create_schema()
    store = VerificationInboxStore(ucs)
    assert store.get() is None
    store.save(VerificationInboxConfig("me@gmail.com", "abcd efgh"))
    assert store.get() == VerificationInboxConfig("me@gmail.com", "abcd efgh")
    store.delete()
    assert store.get() is None
