"""AndroidDriver.get_ui_tree reads the accessibility tree from Portal only when asked to."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mobile_crawler.domain.crawler_agent.tools.driver.android import AndroidDriver
from mobile_crawler.domain.crawler_agent.tools.ui.a11y_completeness import count_nodes

PORTAL_STATE = {
    "a11y_tree": {"className": "FrameLayout", "children": [{"className": "Button", "children": []}]},
    "phone_state": {"currentApp": "Example"},
    "device_context": {"screen_bounds": {"width": 1080, "height": 2400}, "filtering_params": {}},
}


def _driver(use_accessibility: bool) -> AndroidDriver:
    driver = AndroidDriver(serial="test", use_accessibility=use_accessibility)
    driver.device = MagicMock()
    driver.ensure_connected = AsyncMock()
    driver._get_current_app = AsyncMock(return_value="com.example")
    driver._get_device_context = AsyncMock(return_value={"screen_bounds": {"width": 1, "height": 2}})
    return driver


def _portal_client(**kwargs):
    client = MagicMock()
    client.connect = AsyncMock()
    client.get_state = AsyncMock(**kwargs)
    return client


@pytest.mark.asyncio
async def test_tree_is_empty_and_portal_untouched_when_accessibility_is_off():
    driver = _driver(use_accessibility=False)
    with patch("mobile_crawler.domain.crawler_agent.tools.android.portal_client.PortalClient") as portal:
        tree = await driver.get_ui_tree()

    assert tree["a11y_tree"] == []
    assert "a11y_error" not in tree
    portal.assert_not_called()


@pytest.mark.asyncio
async def test_tree_comes_from_portal_when_accessibility_is_on():
    driver = _driver(use_accessibility=True)
    with patch(
        "mobile_crawler.domain.crawler_agent.tools.android.portal_client.PortalClient",
        return_value=_portal_client(return_value=PORTAL_STATE),
    ):
        tree = await driver.get_ui_tree()

    assert tree["a11y_tree"] == PORTAL_STATE["a11y_tree"]
    assert tree["phone_state"] == PORTAL_STATE["phone_state"]
    assert tree["device_context"]["screen_bounds"]["height"] == 2400
    assert "a11y_error" not in tree


@pytest.mark.asyncio
async def test_portal_failure_leaves_an_empty_tree_with_the_reason():
    driver = _driver(use_accessibility=True)
    failing = _portal_client(side_effect=RuntimeError("portal not installed"))
    with patch("mobile_crawler.domain.crawler_agent.tools.android.portal_client.PortalClient", return_value=failing):
        tree = await driver.get_ui_tree()

    assert tree["a11y_tree"] == []
    assert "portal not installed" in tree["a11y_error"]


@pytest.mark.asyncio
async def test_portal_failure_warning_does_not_promise_a_retry(caplog):
    driver = _driver(use_accessibility=True)
    failing = _portal_client(side_effect=RuntimeError("portal not installed"))
    with (
        patch("mobile_crawler.domain.crawler_agent.tools.android.portal_client.PortalClient", return_value=failing),
        caplog.at_level("WARNING"),
    ):
        await driver.get_ui_tree()

    warnings = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert warnings == ["Portal accessibility tree unavailable: portal not installed"]


@pytest.mark.asyncio
async def test_portal_error_status_is_reported_not_treated_as_a_tree():
    driver = _driver(use_accessibility=True)
    errored = _portal_client(return_value={"status": "error", "message": "no active window"})
    with patch("mobile_crawler.domain.crawler_agent.tools.android.portal_client.PortalClient", return_value=errored):
        tree = await driver.get_ui_tree()

    assert tree["a11y_tree"] == []
    assert tree["a11y_error"] == "no active window"


@pytest.mark.asyncio
async def test_a_failed_portal_is_not_retried_until_the_backoff_expires():
    driver = _driver(use_accessibility=True)
    failing = _portal_client(side_effect=RuntimeError("portal not installed"))
    with patch(
        "mobile_crawler.domain.crawler_agent.tools.android.portal_client.PortalClient", return_value=failing
    ) as portal:
        first = await driver.get_ui_tree()
        second = await driver.get_ui_tree()
        driver._portal_retry_at = 0.0  # backoff elapsed
        await driver.get_ui_tree()

    assert failing.get_state.await_count == 2
    assert first["a11y_error"] == second["a11y_error"] == "portal not installed"
    assert portal.call_count == 1  # the client itself is created once


def test_count_nodes_handles_root_dict_list_and_garbage():
    assert count_nodes(PORTAL_STATE["a11y_tree"]) == 2
    assert count_nodes([PORTAL_STATE["a11y_tree"], {"children": []}]) == 3
    assert count_nodes([]) == 0
    assert count_nodes(None) == 0
