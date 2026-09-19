from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mobile_crawler.domain.crawler_agent.tools.driver.android import AndroidDriver


def _driver(shell_output: str) -> AndroidDriver:
    driver = AndroidDriver.__new__(AndroidDriver)
    driver.device = MagicMock()
    driver.device.shell = AsyncMock(return_value=shell_output)
    driver.device.keyevent = AsyncMock()
    driver.ensure_connected = AsyncMock()
    return driver


@pytest.mark.asyncio
async def test_hide_keyboard_sends_back_when_ime_shown():
    driver = _driver("  mInputShown=true\n")
    with patch("asyncio.sleep", new=AsyncMock()):
        assert await driver.hide_keyboard() is True
    driver.device.keyevent.assert_awaited_once_with(4)


@pytest.mark.asyncio
async def test_hide_keyboard_does_not_press_back_when_ime_hidden():
    driver = _driver("  mInputShown=false\n")
    assert await driver.hide_keyboard() is False
    driver.device.keyevent.assert_not_awaited()
