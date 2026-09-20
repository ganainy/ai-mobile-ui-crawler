"""
Portal APK management and device communication utilities.

This module handles downloading, installing, and managing the Mobilerun Portal app
on Android devices. It also provides utilities for checking accessibility service
status and managing device communication modes (TCP and content provider).
"""

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

import requests
from async_adbutils import AdbDevice, adb

from mobile_crawler.config import get_app_data_dir
from mobile_crawler.domain.crawler_agent.tools.driver.android import AndroidDriver

logger = logging.getLogger("crawler_agent")

REPO = "droidrun/mobilerun-portal"

PORTAL_PACKAGE_NAME = "com.mobilerun.portal"
A11Y_SERVICE_NAME = f"{PORTAL_PACKAGE_NAME}/{PORTAL_PACKAGE_NAME}.service.MobilerunAccessibilityService"

# Portal is AGPL-3.0, so it is downloaded from upstream at setup time rather than
# vendored in this repo. The release is pinned by version and SHA-256 (upstream
# publishes both in each release's latest.json). To move to a newer Portal, bump
# both values together.
PORTAL_VERSION = "0.7.25"
PORTAL_APK_SHA256 = "6dc9e8327fcaecf3ba0ad5054f19357d832fc923763fb6c9d1ab09f79e3d3297"
PORTAL_APK_URL = (
    f"https://github.com/{REPO}/releases/download/v{PORTAL_VERSION}/{PORTAL_PACKAGE_NAME}-{PORTAL_VERSION}.apk"
)


def _portal_cache_path() -> Path:
    return get_app_data_dir() / "portal" / f"{PORTAL_PACKAGE_NAME}-{PORTAL_VERSION}.apk"


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextlib.contextmanager
def download_portal_apk(debug: bool = False):
    """Yield the path of the pinned Portal APK, downloading it once and caching it.

    The file is verified against ``PORTAL_APK_SHA256``; a cached file that no longer
    matches is discarded and fetched again.

    Raises:
        RuntimeError: If the downloaded file does not match the pinned SHA-256.
        requests.HTTPError: If the download fails.
    """
    cache = _portal_cache_path()
    if cache.exists() and _sha256_of(cache) != PORTAL_APK_SHA256:
        cache.unlink()

    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading Portal APK {PORTAL_VERSION}")
        if debug:
            logger.debug(f"Portal APK URL: {PORTAL_APK_URL}")
        partial = cache.with_suffix(".part")
        response = requests.get(PORTAL_APK_URL, stream=True, timeout=60)
        response.raise_for_status()
        with partial.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
        if _sha256_of(partial) != PORTAL_APK_SHA256:
            partial.unlink()
            raise RuntimeError(f"Downloaded Portal APK does not match the pinned SHA-256 ({PORTAL_VERSION})")
        partial.replace(cache)

    yield str(cache)


async def enable_portal_accessibility(device: AdbDevice, service_name: str = A11Y_SERVICE_NAME):
    """
    Enable the Portal accessibility service on the device.

    Args:
        device: ADB device connection
        service_name: Full accessibility service name (default: Portal service)

    Note:
        This may fail on some devices due to security restrictions.
        Manual enablement may be required.
    """
    await device.shell(f"settings put secure enabled_accessibility_services {service_name}")
    await device.shell("settings put secure accessibility_enabled 1")


async def check_portal_accessibility(
    device: AdbDevice, service_name: str = A11Y_SERVICE_NAME, debug: bool = False
) -> bool:
    """
    Check if the Portal accessibility service is enabled.

    Args:
        device: ADB device connection
        service_name: Full accessibility service name to check
        debug: Enable debug logging

    Returns:
        True if the accessibility service is enabled, False otherwise
    """
    a11y_services = await device.shell("settings get secure enabled_accessibility_services")
    if service_name not in a11y_services:
        if debug:
            print(a11y_services)
        return False

    a11y_enabled = await device.shell("settings get secure accessibility_enabled")
    if a11y_enabled != "1":
        if debug:
            print(a11y_enabled)
        return False

    return True


async def ping_portal(device: AdbDevice, debug: bool = False):
    """
    Ping the Droidrun Portal to check if it is installed and accessible.
    """
    try:
        packages = await device.list_packages()
    except Exception as e:
        raise Exception("Failed to list packages") from e

    if PORTAL_PACKAGE_NAME not in packages:
        if debug:
            print(packages)
        raise Exception("Portal is not installed on the device")

    if not await check_portal_accessibility(device, debug=debug):
        await device.shell("am start -a android.settings.ACCESSIBILITY_SETTINGS")
        raise Exception("Droidrun Portal is not enabled as an accessibility service on the device")


async def ping_portal_content(device: AdbDevice, debug: bool = False):
    """
    Test Portal accessibility via content provider.

    Args:
        device: ADB device connection
        debug: Enable debug logging

    Raises:
        Exception: If Portal is not reachable via content provider
    """
    try:
        state = await device.shell("content query --uri content://com.mobilerun.portal/state")
        if "Row: 0 result=" not in state:
            raise Exception("Failed to get state from Droidrun Portal")
    except Exception as e:
        raise Exception("Droidrun Portal is not reachable") from e


async def ping_portal_tcp(device: AdbDevice, debug: bool = False):
    """
    Test Portal accessibility via TCP mode.

    Args:
        device: ADB device connection
        debug: Enable debug logging

    Raises:
        Exception: If Portal is not reachable via TCP or port forwarding fails
    """
    try:
        driver = AndroidDriver(serial=device.serial, use_tcp=True)
        await driver.connect()
    except Exception as e:
        raise Exception("Failed to setup TCP forwarding") from e


async def set_overlay_offset(device: AdbDevice, offset: int):
    """
    Set the overlay offset using the /overlay_offset portal content provider endpoint.
    """
    try:
        cmd = f'content insert --uri "content://com.mobilerun.portal/overlay_offset" --bind offset:i:{offset}'
        await device.shell(cmd)
    except Exception as e:
        raise Exception("Error setting overlay offset") from e


async def toggle_overlay(device: AdbDevice, visible: bool):
    """Toggle the overlay visibility.

    Args:
        device: Device to toggle the overlay on
        visible: Whether to show the overlay

    throws:
        Exception: If the overlay toggle fails
    """
    try:
        visible_str = "true" if visible else "false"
        cmd = f'content insert --uri "content://com.mobilerun.portal/overlay_visible" --bind visible:b:{visible_str}'
        await device.shell(cmd)
    except Exception as e:
        raise Exception("Failed to toggle overlay") from e


async def setup_keyboard(device: AdbDevice):
    """
    Set up the Droidrun keyboard as the default input method.
    Simple setup that just switches to Droidrun keyboard without saving/restoring.

    throws:
        Exception: If the keyboard setup fails
    """
    try:
        await device.shell("ime enable com.mobilerun.portal/.input.DroidrunKeyboardIME")
        await device.shell("ime set com.mobilerun.portal/.input.DroidrunKeyboardIME")
    except Exception as e:
        raise Exception("Error setting up keyboard") from e


async def disable_keyboard(
    device: AdbDevice,
    target_ime: str = "com.mobilerun.portal/.input.DroidrunKeyboardIME",
):
    """
    Disable a specific IME (keyboard) and optionally switch to another.
    By default, disables the Droidrun keyboard.

    Args:
        target_ime: The IME package/activity to disable (default: Droidrun keyboard)

    Returns:
        bool: True if disabled successfully, False otherwise
    """
    try:
        await device.shell(f"ime disable {target_ime}")
        return True
    except Exception as e:
        raise Exception("Error disabling keyboard") from e


async def setup_portal(
    device: AdbDevice,
    debug: bool = False,
) -> bool:
    """Download, install, and enable the Portal APK on a device.

    Installs the pinned Portal release (see ``PORTAL_VERSION``).

    Args:
        device: ADB device connection.
        debug: Enable debug logging.

    Returns:
        True if setup completed successfully, False otherwise.
    """
    try:
        apk_context = download_portal_apk(debug)

        with apk_context as apk_path:
            if not os.path.exists(apk_path):
                logger.error(f"APK file not found at {apk_path}")
                return False

            logger.info("Installing Portal APK...")
            try:
                await device.install(apk_path, uninstall=True, flags=["-g"], silent=not debug)
            except Exception as e:
                logger.error(f"Portal installation failed: {e}")
                return False

            logger.info("Portal APK installed")

            try:
                await enable_portal_accessibility(device)
                # Wait for the service to become responsive
                await _wait_for_portal_service(device)
                # The overlay would be screenshotted and parsed as UI elements.
                await toggle_overlay(device, False)
                logger.info("Accessibility service enabled")
            except Exception as e:
                logger.warning(f"Could not auto-enable accessibility service: {e}")
                try:
                    await device.shell("am start -a android.settings.ACCESSIBILITY_SETTINGS")
                except Exception:
                    pass
                return False

        return True

    except Exception as e:
        logger.error(f"Portal setup failed: {e}")
        if debug:
            import traceback

            logger.debug(traceback.format_exc())
        return False


async def _wait_for_portal_service(device: AdbDevice, timeout: float = 10.0, interval: float = 1.0) -> None:
    """Poll the content provider until the accessibility service is responsive.

    Uses the simple ``/state`` endpoint which responds as soon as the
    service process is alive, without requiring an active window.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            state = await device.shell("content query --uri content://com.mobilerun.portal/state")
            if '"status":"success"' in state:
                return
        except Exception:
            pass
        await asyncio.sleep(interval)
    logger.warning("Portal service did not become responsive within timeout")


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version.lstrip("v")))


def _parse_portal_version(raw_output: str) -> str | None:
    """Extract portal version string from content provider output."""
    try:
        if "result=" in raw_output:
            json_str = raw_output.split("result=", 1)[1].strip()
            data = json.loads(json_str)
            if data.get("status") == "success":
                return data.get("result") or data.get("data")
    except Exception:
        pass
    return None


@dataclass
class PortalStatus:
    """Read-only snapshot of Portal's state on a device."""

    installed: bool
    version: str | None
    accessibility_enabled: bool

    @property
    def ready(self) -> bool:
        return self.installed and self.accessibility_enabled

    def describe(self) -> str:
        if not self.installed:
            return "Portal is not installed"
        if not self.accessibility_enabled:
            return "Portal is installed but its accessibility service is off"
        return f"Portal {self.version or '?'} is ready"


async def get_portal_status(device: AdbDevice) -> PortalStatus:
    """Check Portal on *device* without changing anything."""
    packages = await device.list_packages()
    installed = PORTAL_PACKAGE_NAME in packages
    version = None
    if installed:
        raw = await device.shell(f"content query --uri content://{PORTAL_PACKAGE_NAME}/version")
        version = _parse_portal_version(raw) if isinstance(raw, str) else None
    services = await device.shell("settings get secure enabled_accessibility_services")
    return PortalStatus(installed, version, isinstance(services, str) and A11Y_SERVICE_NAME in services)


async def ensure_portal_ready(
    device: AdbDevice,
    debug: bool = False,
) -> None:
    """Run parallel health checks and auto-fix portal issues.

    Performs three checks concurrently:
    1. Is the Portal APK installed?
    2. Is the installed version compatible?
    3. Is the accessibility service enabled?

    If any check fails, attempts to fix automatically (install/upgrade
    APK, enable accessibility).  Raises on unrecoverable failure.

    Args:
        device: ADB device connection.
        debug: Enable debug logging.

    Raises:
        RuntimeError: If portal cannot be made ready after auto-fix.
    """
    # ── parallel checks ──────────────────────────────────────────
    packages_task = device.list_packages()
    version_task = device.shell("content query --uri content://com.mobilerun.portal/version")
    a11y_task = device.shell("settings get secure enabled_accessibility_services")

    packages, version_raw, a11y_services = await asyncio.gather(
        packages_task, version_task, a11y_task, return_exceptions=True
    )

    # If all checks failed, the device is likely unreachable — skip
    # auto-setup and let AndroidDriver.connect() surface the real error.
    if isinstance(packages, Exception) and isinstance(version_raw, Exception) and isinstance(a11y_services, Exception):
        logger.debug(f"Portal health check skipped (device unreachable): {packages}")
        return

    # ── evaluate results ─────────────────────────────────────────
    is_installed = isinstance(packages, list) and PORTAL_PACKAGE_NAME in packages

    installed_version = _parse_portal_version(version_raw) if isinstance(version_raw, str) else None

    a11y_enabled = isinstance(a11y_services, str) and A11Y_SERVICE_NAME in a11y_services

    # Only an older Portal is upgraded; a newer one is left alone.
    needs_upgrade = bool(
        is_installed and installed_version and _version_tuple(installed_version) < _version_tuple(PORTAL_VERSION)
    )
    if needs_upgrade:
        logger.info(f"Portal version mismatch: installed={installed_version}, expected={PORTAL_VERSION}")

    # ── fix if needed ────────────────────────────────────────────
    if not is_installed or needs_upgrade:
        reason = "not installed" if not is_installed else "outdated"
        logger.info(f"Portal {reason}, running auto-setup...")
        success = await setup_portal(device, debug)
        if not success:
            raise RuntimeError(
                f"Portal auto-setup failed ({reason}). "
                "Verify portal setup on the device and review mobile-crawler logs for diagnostics."
            )
        # After install, accessibility is already enabled by setup_portal
        return

    if not a11y_enabled:
        logger.info("Portal accessibility service not enabled, enabling...")
        try:
            await enable_portal_accessibility(device)
            # Verify settings were applied
            if not await check_portal_accessibility(device, debug=debug):
                raise RuntimeError(
                    "Could not enable Portal accessibility service. "
                    "Please enable it manually in device settings, "
                    "or reinstall/re-enable the portal app on the device."
                )
            # Wait for the service process to start and become responsive
            await _wait_for_portal_service(device)
            logger.info("Accessibility service enabled")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Failed to enable accessibility service: {e}. "
                "Verify portal setup on the device and review mobile-crawler logs for diagnostics."
            ) from e


async def test():
    device = await adb.device()
    await ping_portal(device, debug=False)


if __name__ == "__main__":
    asyncio.run(test())
