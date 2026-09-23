"""Pre-run warnings for a Portal without its accessibility service and an unreachable Phoenix."""

from unittest.mock import AsyncMock, patch

import pytest

from mobile_crawler.core.pre_run_warnings import collect_pre_run_warnings
from mobile_crawler.domain.crawler_agent.portal import PortalStatus

PORTAL_STATUS = "mobile_crawler.domain.crawler_agent.portal.get_portal_status"
ADB_DEVICE = "async_adbutils.adb.device"
PHOENIX_REACHABLE = "mobile_crawler.domain.crawler_agent.agent.utils.tracing_setup.check_phoenix_reachable"


class Config:
    def __init__(self, **values):
        self.values = values

    def get(self, key, default=None):
        return self.values.get(key, default)


def _collect(config, portal=PortalStatus(True, "1.0", True), phoenix_up=True, device="dev-1"):
    with (
        patch(ADB_DEVICE, new=AsyncMock()),
        patch(PORTAL_STATUS, new=AsyncMock(return_value=portal)),
        patch(PHOENIX_REACHABLE, return_value=phoenix_up) as reachable,
    ):
        return collect_pre_run_warnings(config, device), reachable


@pytest.mark.parametrize("mode", ["boost", "accessibility"])
def test_warns_when_portal_accessibility_service_is_off(mode):
    warnings, _ = _collect(Config(ui_parser_mode=mode), portal=PortalStatus(True, "1.0", False))

    assert len(warnings) == 1
    assert "accessibility service is off" in warnings[0].message
    assert warnings[0].portal_fix == "enable"


def test_warns_when_portal_is_not_installed():
    warnings, _ = _collect(Config(ui_parser_mode="boost"), portal=PortalStatus(False, None, False))

    assert "Portal is not installed" in warnings[0].message
    assert warnings[0].portal_fix == "install"


def test_no_portal_warning_in_omniparser_mode_or_without_a_device():
    off = PortalStatus(True, "1.0", False)

    assert _collect(Config(ui_parser_mode="omniparser"), portal=off)[0] == []
    assert _collect(Config(ui_parser_mode="boost"), portal=off, device=None)[0] == []


def test_warns_when_phoenix_tracing_is_on_but_unreachable():
    config = Config(ui_parser_mode="omniparser", enable_tracing=True, tracing_provider="phoenix", phoenix_url="http://p:1")

    warnings, reachable = _collect(config, phoenix_up=False)

    assert len(warnings) == 1
    assert "http://p:1" in warnings[0].message
    assert warnings[0].portal_fix is None
    assert reachable.call_args.args[0] == "http://p:1"


@pytest.mark.parametrize(
    "values",
    [
        {"enable_tracing": False, "tracing_provider": "phoenix"},
        {"enable_tracing": True, "tracing_provider": "langfuse"},
    ],
)
def test_no_phoenix_warning_when_phoenix_is_not_in_use(values):
    warnings, reachable = _collect(Config(ui_parser_mode="omniparser", **values), phoenix_up=False)

    assert warnings == []
    reachable.assert_not_called()


def test_a_failing_check_is_skipped():
    config = Config(ui_parser_mode="boost", enable_tracing=True, tracing_provider="phoenix")
    with (
        patch(ADB_DEVICE, new=AsyncMock(side_effect=RuntimeError("adb gone"))),
        patch(PHOENIX_REACHABLE, return_value=False),
    ):
        warnings = collect_pre_run_warnings(config, "dev-1")

    assert len(warnings) == 1
    assert "Phoenix" in warnings[0].message
