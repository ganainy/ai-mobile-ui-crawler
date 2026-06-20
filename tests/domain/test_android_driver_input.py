from unittest.mock import AsyncMock

import pytest

from mobile_crawler.domain.crawler_agent.tools.driver.android import AndroidDriver


def _driver() -> AndroidDriver:
    driver = AndroidDriver(serial="emulator-5554")
    driver._connected = True
    driver.device = AsyncMock()
    return driver


@pytest.mark.asyncio
async def test_input_text_without_clear():
    driver = _driver()
    driver.device.shell = AsyncMock(return_value="")

    await driver.input_text("hello world")

    # Should call shell once to type text with spaces as %s
    driver.device.shell.assert_called_once_with('input text "hello%sworld"')


@pytest.mark.asyncio
async def test_input_text_with_clear():
    driver = _driver()
    driver.device.shell = AsyncMock(return_value="")

    await driver.input_text("hello world", clear=True)

    # Should call shell twice: first to clear, second to type text
    calls = driver.device.shell.await_args_list
    assert len(calls) == 2

    # Check clear command
    clear_cmd = calls[0].args[0]
    assert clear_cmd.startswith("input keyevent")
    assert "123" in clear_cmd  # KEYCODE_MOVE_END
    assert "67" in clear_cmd   # KEYCODE_DEL

    # Check type command
    assert calls[1].args[0] == 'input text "hello%sworld"'


@pytest.mark.asyncio
async def test_input_text_escapes_special_characters():
    driver = _driver()
    driver.device.shell = AsyncMock(return_value="")

    await driver.input_text("hello $`\"\\ world")

    # Check that special shell characters are escaped properly and spaces replaced by %s
    driver.device.shell.assert_called_once_with('input text "hello%s\\$\\`\\"\\\\%sworld"')


@pytest.mark.asyncio
async def test_input_text_empty_string():
    driver = _driver()
    driver.device.shell = AsyncMock(return_value="")

    await driver.input_text("")

    driver.device.shell.assert_called_once_with('input text ""')


@pytest.mark.asyncio
async def test_input_text_long_string():
    driver = _driver()
    driver.device.shell = AsyncMock(return_value="")

    long_text = "a" * 300 + " " + "b" * 300
    await driver.input_text(long_text)

    called_cmd = driver.device.shell.call_args.args[0]
    assert called_cmd.startswith('input text "')
    assert called_cmd.endswith('"')
    # Space should be %s
    assert " " not in called_cmd.split('"')[1]
    assert "%s" in called_cmd


@pytest.mark.asyncio
async def test_input_text_clear_generates_move_end_then_deletes():
    driver = _driver()
    driver.device.shell = AsyncMock(return_value="")

    await driver.input_text("x", clear=True)

    calls = driver.device.shell.await_args_list
    clear_cmd = calls[0].args[0]
    # Must start with MOVE_END (123) and contain DEL (67)
    parts = clear_cmd.split("input keyevent ")[1].split()
    assert parts[0] == "123"  # MOVE_END first
    assert all(p == "67" for p in parts[1:])  # All DEL
    assert len(parts) == 101  # 1 MOVE_END + 100 DEL
