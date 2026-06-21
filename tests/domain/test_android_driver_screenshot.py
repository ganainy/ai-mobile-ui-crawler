import asyncio
import io
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from mobile_crawler.domain.crawler_agent.tools.driver.android import AndroidDriver


def _png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), color=(255, 0, 0)).save(output, format="PNG")
    return output.getvalue()


def _jpeg_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), color=(255, 0, 0)).save(output, format="JPEG")
    return output.getvalue()


def _driver() -> AndroidDriver:
    driver = AndroidDriver(serial="emulator-5554")
    driver._connected = True
    driver.device = AsyncMock()
    return driver


@pytest.mark.asyncio
async def test_screenshot_png_converts_to_jpeg():
    """PNG screenshots from device.screenshot_bytes() are converted to JPEG."""
    driver = _driver()
    driver.device.screenshot_bytes = AsyncMock(return_value=_png_bytes())

    result = await driver.screenshot()

    assert result[:2] == b"\xff\xd8"  # JPEG magic bytes


@pytest.mark.asyncio
async def test_screenshot_invalid_data_retries_then_succeeds():
    """Corrupted PNG (bad magic but PIL fails) triggers a retry, then succeeds."""
    driver = _driver()
    # Valid PNG magic bytes but truncated/corrupted body → PIL.verify() raises
    corrupted = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    driver.device.screenshot_bytes = AsyncMock(
        side_effect=[corrupted, _png_bytes()]
    )

    result = await driver.screenshot()

    assert result[:2] == b"\xff\xd8"
    assert driver.device.screenshot_bytes.await_count == 2


@pytest.mark.asyncio
async def test_screenshot_jpeg_passthrough():
    """Already-JPEG screenshots pass through without re-encoding."""
    driver = _driver()
    jpeg = _jpeg_bytes()
    driver.device.screenshot_bytes = AsyncMock(return_value=jpeg)

    result = await driver.screenshot()

    assert result == jpeg


@pytest.mark.asyncio
async def test_screenshot_string_result_encoded_to_bytes():
    """String results from screenshot_bytes() are encoded to bytes."""
    driver = _driver()
    # Simulate a device that returns a string (some adb libs do this)
    driver.device.screenshot_bytes = AsyncMock(return_value="not real image data")

    # Should not crash; the non-PNG string gets encoded and returned as-is
    result = await driver.screenshot()

    assert isinstance(result, bytes)
