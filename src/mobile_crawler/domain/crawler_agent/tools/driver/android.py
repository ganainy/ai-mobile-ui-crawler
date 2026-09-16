"""AndroidDriver — ADB-based device driver without Portal.

Wraps ``adbutils.Device`` to provide clean device I/O without Portal.
Uses ADB commands for all operations - no special app needed on device.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
from typing import Any

from async_adbutils import adb

from mobile_crawler.domain.crawler_agent.tools.driver.base import DeviceDriver

logger = logging.getLogger("crawler_agent")


class AndroidDriver(DeviceDriver):
    """Raw Android device I/O via ADB only - no Portal needed."""

    platform = "Android"

    supported = {
        "tap",
        "swipe",
        "input_text",
        "press_button",
        "start_app",
        "screenshot",
        "get_ui_tree",
        "get_date",
        "get_apps",
        "list_packages",
        "install_app",
        "drag",
    }

    supported_buttons = {"back", "home", "enter"}

    _BUTTON_KEYCODES = {
        "back": 4,
        "home": 3,
        "enter": 66,
    }

    def __init__(
        self,
        serial: str | None = None,
        status_bar_exclusion_px: int = 0,
        bottom_bar_exclusion_px: int = 0,
    ) -> None:
        self._serial = serial
        self.device = None
        self._connected = False
        self.status_bar_exclusion_px = status_bar_exclusion_px
        self.bottom_bar_exclusion_px = bottom_bar_exclusion_px

    # -- lifecycle -----------------------------------------------------------

    async def connect(self) -> None:
        if self._connected:
            return

        self.device = await adb.device(serial=self._serial)
        state = await self.device.get_state()
        if state != "device":
            raise ConnectionError(f"Device is not online. State: {state}")

        self._connected = True
        logger.info("Connected to Android device via ADB (no Portal)")

    async def ensure_connected(self) -> None:
        if not self._connected:
            await self.connect()

    async def _handle_connection_drop(self, exception: Exception) -> bool:
        """Attempt to recover from a connection drop.

        Returns:
            True if reconnection succeeded and retry can be attempted, False otherwise.
        """
        err_msg = str(exception).lower()
        if any(word in err_msg for word in ["device", "offline", "connection", "closed", "reset", "timeout"]):
            logger.warning(
                f"AndroidDriver detected connection drop: {exception}. "
                f"Attempting to reconnect serial {self._serial}..."
            )
            self._connected = False

            if self._serial:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        'adb', 'connect', self._serial,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    stdout, stderr = await proc.communicate()
                    logger.info(
                        f"AndroidDriver adb connect stdout: {stdout.decode().strip()}, "
                        f"stderr: {stderr.decode().strip()}"
                    )
                    await asyncio.sleep(1.0)
                except Exception as re_err:
                    logger.error(f"Failed to execute adb connect in AndroidDriver: {re_err}")

            try:
                await self.connect()
                logger.info("AndroidDriver successfully reconnected to device.")
                return True
            except Exception as conn_err:
                logger.error(f"AndroidDriver reconnection failed: {conn_err}")
                return False
        return False

    # -- input actions -------------------------------------------------------

    async def tap(self, x: int, y: int) -> None:
        try:
            await self.ensure_connected()
            await self.device.click(x, y)
        except Exception as e:
            if await self._handle_connection_drop(e):
                await self.device.click(x, y)
            else:
                raise

    async def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: float = 1000,
    ) -> None:
        try:
            await self.ensure_connected()
            await self.device.swipe(x1, y1, x2, y2, float(duration_ms / 1000))
            await asyncio.sleep(duration_ms / 1000)
        except Exception as e:
            if await self._handle_connection_drop(e):
                await self.device.swipe(x1, y1, x2, y2, float(duration_ms / 1000))
                await asyncio.sleep(duration_ms / 1000)
            else:
                raise

    async def input_text(self, text: str, clear: bool = False) -> bool:
        try:
            await self.ensure_connected()

            if clear:
                # Clear existing text by moving cursor to end and sending DEL key events in a single command
                keycodes = ["123"] + ["67"] * 100  # KEYCODE_MOVE_END = 123, KEYCODE_DEL = 67
                await self.device.shell(f"input keyevent {' '.join(keycodes)}")

            # Escape special characters for shell
            escaped_text = (
                text.replace('\\', '\\\\')
                .replace('"', '\\"')
                .replace('$', '\\$')
                .replace('`', '\\`')
                .replace(' ', '%s')
            )

            # Use ADB input text
            await self.device.shell(f'input text "{escaped_text}"')
            return True
        except Exception as e:
            if await self._handle_connection_drop(e):
                escaped_text = (
                    text.replace('\\', '\\\\')
                    .replace('"', '\\"')
                    .replace('$', '\\$')
                    .replace('`', '\\`')
                    .replace(' ', '%s')
                )
                if clear:
                    keycodes = ["123"] + ["67"] * 100
                    await self.device.shell(f"input keyevent {' '.join(keycodes)}")
                await self.device.shell(f'input text "{escaped_text}"')
                return True
            else:
                raise

    async def press_button(self, button: str) -> None:
        try:
            await self.ensure_connected()
            button_lower = button.lower()
            if button_lower not in self.supported_buttons:
                raise ValueError(
                    f"Button '{button}' not supported. "
                    f"Supported: {', '.join(sorted(self.supported_buttons))}"
                )
            await self.device.keyevent(self._BUTTON_KEYCODES[button_lower])
        except Exception as e:
            if not isinstance(e, ValueError) and await self._handle_connection_drop(e):
                button_lower = button.lower()
                await self.device.keyevent(self._BUTTON_KEYCODES[button_lower])
            else:
                raise

    async def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float = 3.0,
    ) -> None:
        await self.ensure_connected()
        raise NotImplementedError("Drag is not implemented yet")

    # -- app management ------------------------------------------------------

    async def start_app(self, package: str, activity: str | None = None) -> str:
        await self.ensure_connected()
        try:
            logger.debug(f"Starting app {package} with activity {activity}")
            if not activity:
                dumpsys_output = await self.device.shell(
                    f"cmd package resolve-activity --brief {package}"
                )
                activity = dumpsys_output.splitlines()[1].split("/")[1]

            logger.debug(f"Activity: {activity}")
            await self.device.app_start(package, activity)
            logger.debug(f"App started: {package} with activity {activity}")
            return f"App started: {package} with activity {activity}"
        except Exception as e:
            return f"Failed to start app {package}: {e}"

    async def install_app(self, path: str, **kwargs) -> str:
        await self.ensure_connected()
        if not os.path.exists(path):
            return f"Failed to install app: APK file not found at {path}"

        reinstall = kwargs.get("reinstall", False)
        grant_permissions = kwargs.get("grant_permissions", True)

        logger.debug(
            f"Installing app: {path} with reinstall: {reinstall} "
            f"and grant_permissions: {grant_permissions}"
        )
        result = await self.device.install(
            path,
            nolaunch=True,
            uninstall=reinstall,
            flags=["-g"] if grant_permissions else [],
            silent=True,
        )
        logger.debug(f"Installed app: {path} with result: {result}")
        return result

    async def get_apps(self, include_system: bool = True) -> list[dict[str, str]]:
        """Get list of installed apps using pm command."""
        await self.ensure_connected()

        # Use pm list packages
        filter_flag = "" if include_system else "-3"
        output = await self.device.shell(f"pm list packages {filter_flag}")

        packages = []
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                package_name = line.replace("package:", "").strip()
                # Get app label/info
                label = await self._get_app_label(package_name)
                packages.append(
                    {
                        "package": package_name,
                        "label": label or package_name,
                    }
                )

        return packages

    async def _get_app_label(self, package: str) -> str | None:
        """Get app display label from package."""
        try:
            # Use dumpsys to get app info
            output = await self.device.shell(f"dumpsys package {package}")
            # Try to extract label from application info
            match = re.search(r'application label="([^"]+)"', output)
            if match:
                return match.group(1)
        except Exception:
            pass
        return None

    async def list_packages(self, include_system: bool = False) -> list[str]:
        await self.ensure_connected()
        filter_list = [] if include_system else ["-3"]
        return await self.device.list_packages(filter_list)

    # -- state / observation -------------------------------------------------

    async def screenshot(self, hide_overlay: bool = True) -> bytes:
        """Take screenshot using ADB screencap - no Portal needed.

        The top ``status_bar_exclusion_px`` and bottom ``bottom_bar_exclusion_px``
        pixels (Status Bar Exclusion / Bottom Bar Exclusion, see CONTEXT.md)
        are cropped off before the image reaches any consumer (hashing, OCR
        grounding, AI vision) — see ADR-0002.
        """
        await self.ensure_connected()

        max_screenshot_attempts = 3
        last_error: Exception | None = None

        for attempt in range(1, max_screenshot_attempts + 1):
            try:
                # Use async_adbutils built-in screenshot_bytes method
                result = await self.device.screenshot_bytes()

                # Ensure bytes
                if isinstance(result, str):
                    result = result.encode("utf-8")

                # Check if result starts with PNG magic bytes and convert to JPEG if needed
                if result[:8] == b"\x89PNG\r\n\x1a\n":
                    # It's PNG, validate and convert to JPEG using Pillow
                    import io

                    from PIL import Image

                    with Image.open(io.BytesIO(result)) as img:
                        img.verify()

                    with Image.open(io.BytesIO(result)) as img:
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        img = self._crop_screen(img)
                        output = io.BytesIO()
                        img.save(output, format="JPEG", quality=95)
                        return output.getvalue()

                # Not PNG (likely JPEG already) - crop if configured, else pass through
                if self.status_bar_exclusion_px > 0 or self.bottom_bar_exclusion_px > 0:
                    import io

                    from PIL import Image

                    with Image.open(io.BytesIO(result)) as img:
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        img = self._crop_screen(img)
                        output = io.BytesIO()
                        img.save(output, format="JPEG", quality=95)
                        return output.getvalue()

                return result
            except Exception as e:
                last_error = e
                logger.debug(
                    "Invalid PNG screenshot on attempt %s/%s: %s",
                    attempt,
                    max_screenshot_attempts,
                    e,
                )
                if await self._handle_connection_drop(e):
                    continue
                if attempt < max_screenshot_attempts:
                    await asyncio.sleep(0.2 * attempt)
                else:
                    logger.error(
                        "Screenshot capture failed on attempt %s/%s: %s",
                        attempt,
                        max_screenshot_attempts,
                        e,
                    )
                    raise

        if last_error is not None:
            raise RuntimeError("Screenshot capture failed after retries") from last_error

        raise RuntimeError("Screenshot capture failed after retries")

    def _crop_screen(self, img: "Image.Image") -> "Image.Image":
        """Crop the configured Status Bar / Bottom Bar Exclusion off *img*."""
        top = max(0, self.status_bar_exclusion_px)
        bottom = max(0, self.bottom_bar_exclusion_px)
        width, height = img.size
        if top + bottom <= 0 or top + bottom >= height:
            return img
        return img.crop((0, top, width, height - bottom))

    async def get_ui_tree(self) -> dict[str, Any]:
        """Get UI state - returns structure expected by provider.

        With OmniParser mode, this returns an empty a11y tree since we're
        not using Portal. The provider will use screenshot + OmniParser instead.
        """
        try:
            await self.ensure_connected()
            return {
                "a11y_tree": [],  # Empty - using OmniParser instead
                "phone_state": {
                    "currentApp": await self._get_current_app(),
                },
                "device_context": await self._get_device_context(),
            }
        except Exception as e:
            if await self._handle_connection_drop(e):
                return {
                    "a11y_tree": [],
                    "phone_state": {
                        "currentApp": await self._get_current_app(),
                    },
                    "device_context": await self._get_device_context(),
                }
            else:
                raise

    async def _get_current_app(self) -> str:
        """Get currently focused app package."""
        try:
            output = await self.device.shell("dumpsys window | grep mCurrentFocus")
            match = re.search(r"([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.]+)", output)
            if match:
                return match.group(1)
        except Exception:
            pass
        return ""

    async def _get_device_context(self) -> dict[str, Any]:
        """Get device context (screen size, etc)."""
        try:
            output = await self.device.shell("wm size")
            match = re.search(r"(\d+)x(\d+)", output)
            if match:
                width, height = int(match.group(1)), int(match.group(2))
                return {
                    "screen_bounds": {
                        "width": width,
                        "height": height,
                    }
                }
        except Exception:
            pass
        return {"screen_bounds": {"width": 1080, "height": 1920}}

    async def get_date(self) -> str:
        try:
            await self.ensure_connected()
            result = await self.device.shell("date")
            return result.strip()
        except Exception as e:
            if await self._handle_connection_drop(e):
                result = await self.device.shell("date")
                return result.strip()
            else:
                raise
