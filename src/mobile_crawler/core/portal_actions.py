"""Blocking Portal check / enable / install helpers, shared by the Settings panel and the CLI.

They block on adb (and, for an install, a download), so the GUI runs them off the UI thread.
"""

from __future__ import annotations

import asyncio

# How to turn Portal's accessibility service on by hand, for when the adb route
# (fix_portal) fails. Worded for Samsung/Android 15; stock Android names in brackets.
PORTAL_MANUAL_STEPS = (
    "To turn Portal on by hand, on the phone:\n"
    "1. Settings > Accessibility > Installed apps (stock Android: Downloaded apps) > Mobilerun Portal > "
    "turn it on and tap Allow. (Or open the Portal app and tap 'Enable Now' next to "
    "'Accessibility Service Not Enabled'.)\n"
    "2. If the switch is greyed out ('Restricted setting'): Settings > Apps > Mobilerun Portal > "
    "⋮ (top right) > Allow restricted settings, then repeat step 1.\n"
    "3. If it keeps turning itself off: Settings > Apps > Mobilerun Portal > Battery > Unrestricted. "
    "Force-stopping the Portal app also turns the service off.\n"
    "4. Check: the Portal app no longer shows 'Accessibility Service Not Enabled', or use Check / "
    "'mobile-crawler-cli a11y-portal status'.\n"
    "Not needed for this crawler: 'Connect to Mobilerun' (Sign in with Browser / Use API Key / Custom "
    "Connection, which are for the Mobilerun cloud service), the IP, token and ADB forward command under "
    "Connection Details, and All Files Access. The crawler reads Portal over adb and sets that up itself."
)


def _device(device_id: str):
    from async_adbutils import adb

    return adb.device(serial=device_id)


def check_portal(device_id: str) -> tuple[str, bool]:
    """Return ``(status text, ready)`` for Portal on *device_id*, changing nothing."""
    from mobile_crawler.domain.crawler_agent.portal import get_portal_status

    async def run():
        return await get_portal_status(await _device(device_id))

    try:
        status = asyncio.run(run())
    except Exception as e:
        return f"Could not check Portal: {e}", False
    return status.describe(), status.ready


def install_portal(device_id: str) -> tuple[str, bool]:
    """Download (pinned), install and enable Portal, then report its status."""
    from mobile_crawler.domain.crawler_agent.portal import setup_portal

    async def run():
        return await setup_portal(await _device(device_id))

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


def enable_portal(device_id: str) -> tuple[str, bool]:
    """Turn on the accessibility service of an installed Portal over adb, then report its status."""
    from mobile_crawler.domain.crawler_agent import portal

    async def run():
        device = await _device(device_id)
        await portal.enable_portal_accessibility(device)
        await portal.wait_for_portal_service(device)
        # The overlay would be screenshotted and parsed as UI elements.
        await portal.toggle_overlay(device, False)

    try:
        asyncio.run(run())
    except Exception as e:
        return f"Could not enable Portal over adb: {e}", False
    text, ready = check_portal(device_id)
    if not ready:
        return f"{text} (enabling it over adb did not work; turn it on by hand on the phone)", False
    return text, ready


def fix_portal(device_id: str) -> tuple[str, bool]:
    """Make Portal ready with the least change: nothing if ready, enable if installed, else install."""
    from mobile_crawler.domain.crawler_agent.portal import get_portal_status

    async def status():
        return await get_portal_status(await _device(device_id))

    try:
        current = asyncio.run(status())
    except Exception as e:
        return f"Could not check Portal: {e}", False
    if current.ready:
        return current.describe(), True
    if current.installed:
        return enable_portal(device_id)
    return install_portal(device_id)
