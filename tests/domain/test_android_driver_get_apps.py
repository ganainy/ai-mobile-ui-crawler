"""AndroidDriver.get_apps must not look up labels serially, nor twice."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from mobile_crawler.domain.crawler_agent.tools.driver.android import AndroidDriver


def _driver(packages):
    driver = AndroidDriver(serial="x")
    driver._connected = True
    driver.device = AsyncMock()
    driver.device.shell.return_value = "\n".join(f"package:{p}" for p in packages)
    return driver


@pytest.mark.asyncio
async def test_get_apps_looks_up_labels_concurrently():
    driver = _driver([f"com.example.app{i}" for i in range(10)])
    in_flight = 0
    peak = 0

    async def slow_label(package):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return package.upper()

    driver._get_app_label = slow_label
    apps = await driver.get_apps()

    assert peak > 1
    assert [a["package"] for a in apps] == [f"com.example.app{i}" for i in range(10)]
    assert apps[0]["label"] == "COM.EXAMPLE.APP0"


@pytest.mark.asyncio
async def test_get_apps_reuses_labels_while_package_list_is_unchanged():
    driver = _driver(["com.a", "com.b"])
    driver._get_app_label = AsyncMock(return_value="L")

    await driver.get_apps()
    await driver.get_apps()

    assert driver._get_app_label.await_count == 2
