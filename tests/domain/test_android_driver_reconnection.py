from unittest.mock import AsyncMock, patch

import pytest

from mobile_crawler.domain.crawler_agent.tools.driver.android import AndroidDriver


def _driver() -> AndroidDriver:
    driver = AndroidDriver(serial="emulator-5554")
    driver._connected = True
    driver.device = AsyncMock()
    return driver


@pytest.mark.asyncio
@patch('mobile_crawler.domain.crawler_agent.tools.driver.android.asyncio.create_subprocess_exec')
async def test_android_driver_tap_reconnect_success(mock_subprocess_exec):
    driver = _driver()

    # Mock subprocess connect call
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"connected to emulator-5554", b""))
    mock_subprocess_exec.return_value = mock_proc

    # Mock device click side effect: first call raises exception, second succeeds
    driver.device.click = AsyncMock(side_effect=[Exception("device offline"), None])

    # Mock connect method of AndroidDriver so it doesn't try to connect to a real device
    driver.connect = AsyncMock()

    # Execute tap
    await driver.tap(100, 200)

    # Assert reconnect subprocess was called
    mock_subprocess_exec.assert_called_once_with(
        'adb', 'connect', 'emulator-5554',
        stdout=-1, stderr=-1
    )

    # Assert connect was called to reset device
    driver.connect.assert_called_once()

    # Assert device.click was called twice (initial failed attempt + retry)
    assert driver.device.click.call_count == 2


@pytest.mark.asyncio
@patch('mobile_crawler.domain.crawler_agent.tools.driver.android.asyncio.create_subprocess_exec')
async def test_android_driver_tap_reconnect_failure(mock_subprocess_exec):
    driver = _driver()

    # Mock subprocess connect call
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
    mock_subprocess_exec.return_value = mock_proc

    # Mock device click side effect: always raises exception
    driver.device.click = AsyncMock(side_effect=Exception("device offline"))

    # Mock connect method to fail during recovery
    driver.connect = AsyncMock(side_effect=Exception("connection failed"))

    # Execute tap and expect it to raise original exception (or failure exception)
    with pytest.raises(Exception, match="device offline"):
        await driver.tap(100, 200)

    # Assert device.click was called only once (failed and couldn't retry)
    assert driver.device.click.call_count == 1
