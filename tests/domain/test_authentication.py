"""Authentication as first Guided Scenario: agent tools, attempt cap, Human Fallback routing."""

from datetime import UTC, datetime

import pytest

from mobile_crawler.domain.authentication import AuthenticationSession
from mobile_crawler.domain.human_fallback import (
    HumanFallback,
    HumanFallbackConfig,
    HumanReply,
    RequestKind,
)
from mobile_crawler.infrastructure.app_account_store import AppAccount
from mobile_crawler.infrastructure.sms_reader import SmsReadResult, SmsReadStatus
from mobile_crawler.infrastructure.verification_inbox import (
    InboxTimeoutError,
    VerificationInboxConfig,
    VerificationResult,
)

PKG = "com.foo.app"


class FakeAccountStore:
    def __init__(self, account=None):
        self.account = account
        self.saved = []

    def get(self, pkg):
        return self.account

    def save(self, pkg, account):
        self.saved.append((pkg, account))
        self.account = account


class FakeInbox:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def wait_for_verification(self, recipient, since, timeout_seconds):
        self.calls.append(recipient)
        if self.error:
            raise self.error
        return self.result


class FakeSms:
    def __init__(self, result):
        self.result = result

    async def read_otp(self, serial, since_ms=None, timeout_seconds=60.0):
        return self.result


def fallback(reply="__unset__", enabled=True):
    calls = []

    def prompter(request, timeout):
        calls.append(request)
        return reply if reply != "__unset__" else HumanReply(code="999111")

    return HumanFallback(HumanFallbackConfig(enabled=enabled), prompter), calls


def make(account=None, inbox=None, sms=None, human=None, max_attempts=3, inbox_config="on"):
    cfg = VerificationInboxConfig("crawl@gmail.com", "pw") if inbox_config == "on" else None
    return AuthenticationSession(
        app_package=PKG,
        device_id="dev1",
        account_store=FakeAccountStore(account),
        inbox_config=cfg,
        inbox_reader=inbox,
        sms_reader=sms,
        human_fallback=human or fallback()[0],
        max_attempts=max_attempts,
    )


@pytest.mark.asyncio
async def test_signup_saves_created_account():
    s = make()
    tools = s.tools()
    result = await tools["save_app_account"]["function"](
        username="crawl+com.foo.app@gmail.com", password="Pw1!", ctx=None
    )
    assert result[0] is True
    pkg, account = s.account_store.saved[0]
    assert pkg == PKG and account.username == "crawl+com.foo.app@gmail.com" and account.password == "Pw1!"


def test_goal_section_signup_when_no_account():
    text = make().goal_section()
    assert "sign up" in text.lower()
    assert "never try to log in" in text.lower()
    assert "crawl+com.foo.app@gmail.com" in text
    assert "save_app_account" in text


def test_goal_section_uses_address_override_for_signup():
    s = make()
    s.address_override = "me@x.com"
    assert "me@x.com" in s.goal_section()


def test_goal_section_relogin_when_account_exists():
    text = make(account=AppAccount("bob", "secret")).goal_section()
    assert "log in" in text.lower() and "bob" in text and "secret" in text
    assert "save_app_account" not in text


def test_goal_section_relogin_instruction_covers_later_logout():
    text = make(account=AppAccount("bob", "secret")).goal_section()
    assert "logged out" in text.lower() or "log out" in text.lower()


@pytest.mark.asyncio
async def test_get_email_code_success():
    inbox = FakeInbox(VerificationResult(code="123456", link=None, received_at=datetime.now(UTC)))
    result = await make(inbox=inbox).tools()["get_email_code"]["function"](ctx=None)
    assert result[0] is True and "123456" in result[1]
    assert inbox.calls == ["crawl+com.foo.app@gmail.com"]


@pytest.mark.asyncio
async def test_get_email_code_returns_link():
    inbox = FakeInbox(VerificationResult(code=None, link="https://x/verify", received_at=datetime.now(UTC)))
    result = await make(inbox=inbox).tools()["get_email_code"]["function"](ctx=None)
    assert result[0] is True and "https://x/verify" in result[1]


@pytest.mark.asyncio
async def test_email_failure_routes_to_human_fallback_code():
    human, calls = fallback(HumanReply(code="777222"))
    s = make(inbox=FakeInbox(error=InboxTimeoutError("none")), human=human)
    result = await s.tools()["get_email_code"]["function"](ctx=None)
    assert result[0] is True and "777222" in result[1]
    assert calls[0].kind is RequestKind.CODE


@pytest.mark.asyncio
async def test_email_failure_without_inbox_configured_uses_fallback():
    human, calls = fallback(HumanReply(code="555000"))
    s = make(inbox=None, human=human, inbox_config=None)
    result = await s.tools()["get_email_code"]["function"](ctx=None)
    assert "555000" in result[1] and len(calls) == 1


@pytest.mark.asyncio
async def test_failure_with_fallback_off_skips_authentication():
    human, _ = fallback(enabled=False)
    s = make(inbox=FakeInbox(error=InboxTimeoutError("none")), human=human)
    result = await s.tools()["get_email_code"]["function"](ctx=None)
    assert result[0] is False and "skip authentication" in result[1].lower()
    assert s.skipped_reason and "authentication skipped" in s.skipped_reason


@pytest.mark.asyncio
async def test_fallback_timeout_skips_authentication():
    human, _ = fallback(reply=None)
    s = make(inbox=FakeInbox(error=InboxTimeoutError("none")), human=human)
    result = await s.tools()["get_email_code"]["function"](ctx=None)
    assert result[0] is False and s.skipped_reason


@pytest.mark.asyncio
async def test_get_sms_code_success():
    s = make(sms=FakeSms(SmsReadResult(SmsReadStatus.FOUND, code="4321", sender="X")))
    result = await s.tools()["get_sms_code"]["function"](ctx=None)
    assert result[0] is True and "4321" in result[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [SmsReadStatus.UNREADABLE, SmsReadStatus.TIMEOUT])
async def test_sms_failure_routes_to_human_fallback(status):
    human, calls = fallback(HumanReply(code="246810"))
    s = make(sms=FakeSms(SmsReadResult(status)), human=human)
    result = await s.tools()["get_sms_code"]["function"](ctx=None)
    assert result[0] is True and "246810" in result[1]
    assert calls[0].kind is RequestKind.CODE


@pytest.mark.asyncio
async def test_attempt_cap_reached_stops_tools_and_skips_auth():
    human, calls = fallback(enabled=False)
    s = make(inbox=FakeInbox(error=InboxTimeoutError("none")), human=human, max_attempts=2)
    fn = s.tools()["get_email_code"]["function"]
    await fn(ctx=None)
    await fn(ctx=None)
    calls_before = list(s.inbox_reader.calls)
    result = await fn(ctx=None)
    assert result[0] is False and "attempt" in result[1].lower()
    assert s.inbox_reader.calls == calls_before  # no further inbox access
    assert s.skipped_reason


@pytest.mark.asyncio
async def test_cap_shared_across_email_and_sms_tools():
    s = make(
        inbox=FakeInbox(VerificationResult("1234", None, datetime.now(UTC))),
        sms=FakeSms(SmsReadResult(SmsReadStatus.FOUND, code="9876")),
        max_attempts=1,
    )
    await s.tools()["get_email_code"]["function"](ctx=None)
    result = await s.tools()["get_sms_code"]["function"](ctx=None)
    assert result[0] is False


@pytest.mark.asyncio
async def test_skip_authentication_tool_records_reason():
    s = make()
    result = await s.tools()["skip_authentication"]["function"](reason="app needs a phone number", ctx=None)
    assert result[0] is True
    assert "app needs a phone number" in s.skipped_reason


def test_tool_specs_have_description_and_parameters():
    for name, spec in make().tools().items():
        assert spec["description"] and "parameters" in spec and callable(spec["function"]), name
