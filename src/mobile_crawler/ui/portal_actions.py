"""Blocking Portal check / install helpers for the Settings panel (run them off the UI thread)."""

from __future__ import annotations

import asyncio


def check_portal(device_id: str) -> tuple[str, bool]:
    """Return ``(status text, ready)`` for Portal on *device_id*, changing nothing."""
    from async_adbutils import adb

    from mobile_crawler.domain.crawler_agent.portal import get_portal_status

    async def run():
        return await get_portal_status(await adb.device(serial=device_id))

    try:
        status = asyncio.run(run())
    except Exception as e:
        return f"Could not check Portal: {e}", False
    return status.describe(), status.ready


def install_portal(device_id: str) -> tuple[str, bool]:
    """Download (pinned), install and enable Portal, then report its status."""
    from async_adbutils import adb

    from mobile_crawler.domain.crawler_agent.portal import setup_portal

    async def run():
        return await setup_portal(await adb.device(serial=device_id))

    try:
        installed = asyncio.run(run())
    except Exception as e:
        return f"Portal install failed: {e}", False
    if not installed:
        return (
            "Portal install did not finish. If Android asked for confirmation, accept it on the phone; "
            "or enable the accessibility service manually in Settings > Accessibility.",
            False,
        )
    return check_portal(device_id)
