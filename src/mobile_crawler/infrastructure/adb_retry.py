"""Retry adb commands that fail because the wireless link is flaky (not because the answer is 'no')."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

_TRANSIENT_MARKERS = ("timed out", "timeout", "offline", "no devices", "closed", "connection", "unreachable")


def is_transient_adb_failure(output: str, retcode: int) -> bool:
    """True when a failed adb call looks like a link problem. 'No such file' is a real answer, never transient."""
    if retcode == 0:
        return False
    text = (output or "").lower()
    if "no such file" in text:
        return False
    if "device" in text and "not found" in text:  # "device '172.20.10.6:33109' not found"
        return True
    return any(marker in text for marker in _TRANSIENT_MARKERS)


async def run_with_retry(
    run: Callable[[], Awaitable[tuple[str, int]]],
    what: str,
    attempts: int = 4,
    delay_seconds: float = 10.0,
) -> tuple[str, int]:
    """Call ``run()`` until it succeeds, fails for a non-transient reason, or attempts are used up.

    The pause grows linearly (delay, 2*delay, ...). Used for the PCAPdroid stop and the end-of-run video and
    pcap pulls: a dropped link used to mean PCAPdroid kept capturing for days and the files were never pulled.
    """
    attempts = max(1, int(attempts))
    output, retcode = "", 1
    for attempt in range(1, attempts + 1):
        output, retcode = await run()
        if not is_transient_adb_failure(output, retcode) or attempt == attempts:
            break
        logger.warning("%s: transient adb failure (attempt %d/%d): %r; retrying", what, attempt, attempts, (output or "")[:120])
        await asyncio.sleep(delay_seconds * attempt)
    return output, retcode
