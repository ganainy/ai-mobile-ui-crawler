"""Read verification SMS from a connected device over adb (see CONTEXT.md, Verification Challenge).

The device is not rooted, so reading relies on `content query` against the SMS
provider. When adb cannot read it the result is UNREADABLE so the caller can
fall back to a human. Standalone: no agent dependency.
"""

import asyncio
import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

logger = logging.getLogger(__name__)

NO_SIM_WARNING = (
    "No SIM detected on the device. Apps that require a phone number or an SMS "
    "verification code will not work in this run."
)

_ROW_SPLIT = re.compile(r"^Row: \d+ ", re.MULTILINE)
_ROW_FIELDS = re.compile(r"address=(.*?), body=(.*), date=(\d+)\s*$", re.DOTALL)
_OTP = re.compile(r"(?<!\d)\d{4,8}(?!\d)")
_READ_ERRORS = ("Permission Denial", "SecurityException", "Error while accessing provider")


class _ADB(Protocol):
    async def execute_async(
        self, command_list: list[str], suppress_stderr: bool = False, timeout: float | None = None
    ) -> tuple[str, int]: ...


class SmsReadStatus(Enum):
    FOUND = "found"
    TIMEOUT = "timeout"
    UNREADABLE = "unreadable"


@dataclass(frozen=True)
class SmsReadResult:
    status: SmsReadStatus
    code: str | None = None
    sender: str | None = None
    message: str = ""


@dataclass(frozen=True)
class _Sms:
    sender: str
    body: str
    date_ms: int


def extract_otp(body: str) -> str | None:
    """Return the first standalone 4-8 digit number in an SMS body."""
    match = _OTP.search(body)
    return match.group(0) if match else None


def _parse_rows(output: str) -> list[_Sms]:
    messages = []
    for chunk in _ROW_SPLIT.split(output)[1:]:
        fields = _ROW_FIELDS.search(chunk)
        if fields:
            messages.append(_Sms(fields.group(1), fields.group(2), int(fields.group(3))))
    return messages


class SmsReader:
    """Detects a SIM and extracts OTP codes from incoming SMS."""

    def __init__(
        self,
        adb_client: _ADB,
        poll_interval_seconds: float = 2.0,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ):
        self._adb = adb_client
        self._poll_interval = poll_interval_seconds
        self._sleep = sleep or asyncio.sleep

    async def has_sim(self, serial: str) -> bool:
        output, code = await self._adb.execute_async(
            ["-s", serial, "shell", "getprop", "gsm.sim.state"], suppress_stderr=True
        )
        if code != 0:
            return False
        # Dual-SIM devices report e.g. "READY,ABSENT".
        return "READY" in output.upper().split(",")

    async def check_sim(self, serial: str) -> str | None:
        """Return NO_SIM_WARNING when the device cannot receive SMS, else None."""
        return None if await self.has_sim(serial) else NO_SIM_WARNING

    async def read_otp(self, serial: str, since_ms: int | None = None, timeout_seconds: float = 60.0) -> SmsReadResult:
        """Wait up to `timeout_seconds` for an SMS newer than `since_ms` (device epoch ms).

        `since_ms` defaults to the device's current time.
        """
        if since_ms is None:
            since_ms = await self._device_now_ms(serial)

        elapsed = 0.0
        while True:
            output, code = await self._adb.execute_async(
                [
                    "-s",
                    serial,
                    "shell",
                    "content",
                    "query",
                    "--uri",
                    "content://sms/inbox",
                    "--projection",
                    "address:body:date",
                    "--sort",
                    "'date DESC'",
                ],
                suppress_stderr=True,
            )
            if code != 0 or any(err in output for err in _READ_ERRORS):
                logger.warning("Cannot read SMS over adb: %s", output)
                return SmsReadResult(SmsReadStatus.UNREADABLE, message=output)

            for sms in sorted(_parse_rows(output), key=lambda m: m.date_ms, reverse=True):
                if sms.date_ms < since_ms:
                    continue
                otp = extract_otp(sms.body)
                if otp:
                    return SmsReadResult(SmsReadStatus.FOUND, code=otp, sender=sms.sender)

            if elapsed >= timeout_seconds:
                return SmsReadResult(SmsReadStatus.TIMEOUT, message=f"No OTP SMS within {timeout_seconds:g}s")
            await self._sleep(self._poll_interval)
            elapsed += self._poll_interval

    async def _device_now_ms(self, serial: str) -> int:
        output, code = await self._adb.execute_async(["-s", serial, "shell", "date", "+%s"], suppress_stderr=True)
        if code == 0 and output.strip().isdigit():
            return int(output.strip()) * 1000
        return int(time.time() * 1000)
