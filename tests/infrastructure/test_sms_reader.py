"""Tests for SmsReader with mocked adb output."""

import pytest

from mobile_crawler.infrastructure.sms_reader import (
    NO_SIM_WARNING,
    SmsReader,
    SmsReadStatus,
    extract_otp,
)


class FakeADB:
    """Maps a substring of the adb command to a canned (output, returncode)."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def execute_async(self, command_list, suppress_stderr=False, timeout=None):
        joined = " ".join(command_list)
        self.calls.append(joined)
        for key, value in self.responses.items():
            if key in joined:
                if callable(value):
                    value = value()
                return value
        return "", 1


def row(i, address, body, date):
    return f"Row: {i} address={address}, body={body}, date={date}"


def make_reader(responses, **kwargs):
    async def no_sleep(_):
        return None

    return SmsReader(FakeADB(responses), sleep=no_sleep, **kwargs)


@pytest.mark.parametrize(
    "state,expected",
    [("READY", True), ("READY,ABSENT", True), ("ABSENT", False), ("NOT_READY", False), ("", False)],
)
@pytest.mark.asyncio
async def test_has_sim(state, expected):
    reader = make_reader({"gsm.sim.state": (state, 0)})
    assert await reader.has_sim("emu-1") is expected


@pytest.mark.asyncio
async def test_has_sim_false_when_adb_fails():
    reader = make_reader({"gsm.sim.state": ("error", 1)})
    assert await reader.has_sim("emu-1") is False


@pytest.mark.asyncio
async def test_check_sim_returns_warning_without_sim():
    reader = make_reader({"gsm.sim.state": ("ABSENT", 0)})
    assert await reader.check_sim("emu-1") == NO_SIM_WARNING


@pytest.mark.asyncio
async def test_check_sim_returns_none_with_sim():
    reader = make_reader({"gsm.sim.state": ("READY", 0)})
    assert await reader.check_sim("emu-1") is None


@pytest.mark.parametrize(
    "body,code",
    [
        ("Your code is 482913. Do not share it.", "482913"),
        ("G-123456 is your Google verification code", "123456"),
        ("Use 7788 to log in", "7788"),
        ("Call 5551234567890 now", None),
        ("No digits here", None),
    ],
)
def test_extract_otp(body, code):
    assert extract_otp(body) == code


@pytest.mark.asyncio
async def test_read_otp_finds_newest_in_window():
    out = "\n".join(
        [
            row(0, "SHOP", "Code 111111, expires soon", 2000),
            row(1, "BANK", "Old code 999999", 500),
        ]
    )
    reader = make_reader({"content query": (out, 0), "date +%s": ("1", 0)})
    result = await reader.read_otp("emu-1", since_ms=1000, timeout_seconds=1)
    assert result.status is SmsReadStatus.FOUND
    assert result.code == "111111"
    assert result.sender == "SHOP"


@pytest.mark.asyncio
async def test_read_otp_ignores_messages_before_window_and_times_out():
    out = row(0, "BANK", "Old code 999999", 500)
    reader = make_reader({"content query": (out, 0)}, poll_interval_seconds=0.5)
    result = await reader.read_otp("emu-1", since_ms=1000, timeout_seconds=1)
    assert result.status is SmsReadStatus.TIMEOUT
    assert result.code is None


@pytest.mark.asyncio
async def test_read_otp_handles_multiline_body_with_commas():
    out = "Row: 0 address=SHOP, body=Hi, your code\nis 246810, thanks, date=3000"
    reader = make_reader({"content query": (out, 0)})
    result = await reader.read_otp("emu-1", since_ms=1000, timeout_seconds=1)
    assert result.code == "246810"


@pytest.mark.asyncio
async def test_read_otp_unreadable_when_permission_denied():
    denied = "java.lang.SecurityException: Permission Denial: opening provider"
    reader = make_reader({"content query": (denied, 255)})
    result = await reader.read_otp("emu-1", since_ms=1000, timeout_seconds=1)
    assert result.status is SmsReadStatus.UNREADABLE
    assert "Permission Denial" in result.message


@pytest.mark.asyncio
async def test_read_otp_polls_until_message_arrives():
    outputs = iter(["No result found.", "No result found.", row(0, "X", "code 135790", 5000)])
    reader = make_reader({"content query": lambda: (next(outputs), 0)})
    result = await reader.read_otp("emu-1", since_ms=1000, timeout_seconds=10)
    assert result.code == "135790"


@pytest.mark.asyncio
async def test_read_otp_defaults_since_to_device_time():
    out = "\n".join([row(0, "X", "new 222222", 9_000_000), row(1, "X", "old 333333", 100)])
    reader = make_reader({"date +%s": ("5000", 0), "content query": (out, 0)})
    result = await reader.read_otp("emu-1", timeout_seconds=1)
    assert result.code == "222222"


@pytest.mark.parametrize(
    "output,code,expected",
    [
        ("Row: 0 number=+491701234567", 0, "+491701234567"),
        ("Row: 0 number=\nRow: 1 number=0170 1234567", 0, "0170 1234567"),
        ("Row: 0 number=", 0, None),
        ("Row: 0 number=123", 0, None),
        ("Error while accessing provider:telephony", 0, None),
        ("", 1, None),
    ],
)
@pytest.mark.asyncio
async def test_read_own_number(output, code, expected):
    reader = make_reader({"content://telephony/siminfo": (output, code)})
    assert await reader.read_own_number("emu-1") == expected
