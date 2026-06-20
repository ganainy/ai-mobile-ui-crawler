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


def _driver() -> AndroidDriver:
    driver = AndroidDriver(serial="emulator-5554")
    driver._connected = True
    driver.device = AsyncMock()
    return driver


@pytest.mark.asyncio
async def test_screenshot_exec_out_png_converts_to_jpeg():
    driver = _driver()

    with patch.object(driver, "_capture_png_exec_out", AsyncMock(return_value=_png_bytes())):
        result = await driver.screenshot()

    assert result[:2] == b"\xff\xd8"


@pytest.mark.asyncio
async def test_screenshot_invalid_png_retries_with_fresh_capture():
    driver = _driver()
    captures = AsyncMock(side_effect=[b"not a png", _png_bytes()])

    with patch.object(driver, "_capture_png_exec_out", captures):
        result = await driver.screenshot()

    assert result[:2] == b"\xff\xd8"
    assert captures.await_count == 2


@pytest.mark.asyncio
async def test_screenshot_remote_fallback_uses_unique_paths_and_deletes():
    driver = _driver()
    driver.device.shell = AsyncMock()
    driver.device.sync.read_bytes = AsyncMock(side_effect=[b"bad", _png_bytes()])

    with patch.object(driver, "_capture_png_exec_out", AsyncMock(side_effect=RuntimeError("exec-out failed"))):
        result = await driver.screenshot()

    assert result[:2] == b"\xff\xd8"
    screencap_paths = [
        call.args[0].split()[-1]
        for call in driver.device.shell.await_args_list
        if call.args and call.args[0].startswith("screencap -p ")
    ]
    delete_paths = [
        call.args[0].split()[-1]
        for call in driver.device.shell.await_args_list
        if call.args and call.args[0].startswith("rm -f ")
    ]
    assert len(screencap_paths) == 2
    assert len(set(screencap_paths)) == 2
    assert delete_paths == screencap_paths


@pytest.mark.asyncio
async def test_concurrent_screenshot_calls_are_serialized_by_lock():
    driver = _driver()
    active = 0
    max_active = 0

    async def capture():
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return _png_bytes()

    with patch.object(driver, "_capture_png_exec_out", capture):
        await asyncio.gather(driver.screenshot(), driver.screenshot(), driver.screenshot())

    assert max_active == 1
