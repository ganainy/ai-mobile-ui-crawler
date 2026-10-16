import asyncio

import pytest

from mobile_crawler.infrastructure import adb_retry
from mobile_crawler.infrastructure.adb_retry import is_transient_adb_failure, run_with_retry


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)

    monkeypatch.setattr(adb_retry.asyncio, "sleep", fake_sleep)
    return sleeps


@pytest.mark.parametrize(
    "out,code,expected",
    [
        ("Command timed out after 30.0s", 1, True),
        ("error: device offline", 1, True),
        ("adb: device '172.20.10.6:33109' not found", 1, True),
        ("", 0, False),
        ("test: /sdcard/x: No such file or directory", 1, False),
        ("", 1, False),
    ],
)
def test_transient_detection(out, code, expected):
    assert is_transient_adb_failure(out, code) is expected


def test_retries_until_the_link_is_back(no_sleep):
    results = [("Command timed out", 1), ("device offline", 1), ("ok", 0)]
    calls = []

    async def run():
        calls.append(1)
        return results[len(calls) - 1]

    assert asyncio.run(run_with_retry(run, "pull", attempts=4, delay_seconds=10)) == ("ok", 0)
    assert len(calls) == 3 and no_sleep == [10, 20]


def test_real_answers_are_not_retried(no_sleep):
    calls = []

    async def run():
        calls.append(1)
        return "No such file or directory", 1

    assert asyncio.run(run_with_retry(run, "check", attempts=4, delay_seconds=10)) == ("No such file or directory", 1)
    assert len(calls) == 1 and no_sleep == []


def test_gives_up_after_all_attempts(no_sleep):
    calls = []

    async def run():
        calls.append(1)
        return "Command timed out", 1

    assert asyncio.run(run_with_retry(run, "stop", attempts=3, delay_seconds=1)) == ("Command timed out", 1)
    assert len(calls) == 3
