"""Things outside the crawler that make a crawl impossible, classified into a clear user-facing message.

A black (secure-window) screenshot means the app hides its screen from capture; a dead device connection
means nothing can be read or tapped. Either way retrying or relaunching the app cannot help, so the run stops.
"""

from __future__ import annotations

import io

KIND_SCREENSHOT_BLOCKED = "screenshot_blocked"
KIND_DEVICE_LOST = "device_lost"

# Settings packages: the agent must never wander into the device's own settings (Developer Options,
# Wi-Fi, ADB...), because changing them can cut the connection the crawl depends on.
SETTINGS_PACKAGES = frozenset({"com.android.settings", "com.samsung.android.settings"})

# A JPEG of a pure black screen decodes to values a little above 0.
_BLANK_MAX_LUMINANCE = 8
# Overlays the app cannot hide (e.g. Samsung's edge-panel handle, ~0.2% of the pixels) don't count.
_BLANK_MAX_BRIGHT_FRACTION = 0.01


class CrawlBlockedError(RuntimeError):
    """The crawl cannot continue for a reason outside the crawler. ``kind`` is one of the ``KIND_*`` values."""

    def __init__(self, message: str, kind: str) -> None:
        super().__init__(message)
        self.kind = kind


def screenshot_blocked_error(package: str | None) -> CrawlBlockedError:
    who = f"'{package}'" if package else "The app"
    return CrawlBlockedError(
        f"{who} shows a black screenshot, so it blocks screen capture (secure window / integrity check), "
        "and the crawl was stopped. This is an integrity/security check: the app may be refusing to run "
        "because of a device condition (no screen lock PIN/password set, Developer Options or USB/wireless "
        "debugging on, root, emulator) or hiding its screen on purpose. Whatever the on-screen text says, "
        "check the device for those conditions, then start again.",
        KIND_SCREENSHOT_BLOCKED,
    )


def device_lost_error(serial: str | None, detail: str) -> CrawlBlockedError:
    who = f"device {serial}" if serial else "the device"
    return CrawlBlockedError(
        f"The ADB connection to {who} was lost and could not be restored ({detail}), so the crawl was stopped. "
        "Check the cable or wireless-debugging pairing and start again.",
        KIND_DEVICE_LOST,
    )


def is_blank_screenshot(data: bytes | None) -> bool:
    """True when the image is (almost) entirely black. Undecodable or missing data is not 'blank'."""
    if not data:
        return False
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as img:
            histogram = img.convert("L").histogram()
    except Exception:
        return False
    bright = sum(histogram[_BLANK_MAX_LUMINANCE + 1 :])
    return bright / max(sum(histogram), 1) < _BLANK_MAX_BRIGHT_FRACTION


def find_crawl_blocked_error(exc: BaseException | None) -> CrawlBlockedError | None:
    """The ``CrawlBlockedError`` in ``exc``'s cause chain (agents re-wrap it), if any."""
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        if isinstance(exc, CrawlBlockedError):
            return exc
        seen.add(id(exc))
        exc = exc.__cause__ or exc.__context__
    return None
