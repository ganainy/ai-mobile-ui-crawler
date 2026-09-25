"""Pre-run warnings for a Portal without its accessibility service and an unreachable Phoenix."""

from unittest.mock import AsyncMock, patch

import pytest

from mobile_crawler.core.pre_run_warnings import collect_pre_run_warnings
from mobile_crawler.domain.crawler_agent.portal import PortalStatus

PORTAL_STATUS = "mobile_crawler.domain.crawler_agent.portal.get_portal_status"
ADB_DEVICE = "async_adbutils.adb.device"
PHOENIX_REACHABLE = "mobile_crawler.domain.crawler_agent.agent.utils.tracing_setup.check_phoenix_reachable"
LOCAL_PHOENIX = "mobile_crawler.infrastructure.phoenix_docker.PhoenixDockerService"


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


@pytest.mark.parametrize(("mode", "blocks"), [("accessibility", True), ("boost", False)])
def test_portal_problem_blocks_the_run_only_in_accessibility_mode(mode, blocks):
    for portal in (PortalStatus(True, "1.0", False), PortalStatus(False, None, False)):
        warnings, _ = _collect(Config(ui_parser_mode=mode), portal=portal)

        assert warnings[0].blocks_run is blocks


def test_no_portal_warning_in_omniparser_mode_or_without_a_device():
    off = PortalStatus(True, "1.0", False)

    assert _collect(Config(ui_parser_mode="omniparser"), portal=off)[0] == []
    assert _collect(Config(ui_parser_mode="boost"), portal=off, device=None)[0] == []


def test_warns_when_a_remote_phoenix_is_unreachable():
    config = Config(ui_parser_mode="omniparser", enable_tracing=True, tracing_provider="phoenix", phoenix_url="http://p:1")

    warnings, reachable = _collect(config, phoenix_up=False)

    assert len(warnings) == 1
    assert "http://p:1" in warnings[0].message
    assert warnings[0].portal_fix is None
    assert reachable.call_args.args[0] == "http://p:1"
    assert "not on this machine" in warnings[0].message


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


def _local_phoenix(reachable=False, port_in_use=False):
    return (
        patch(f"{LOCAL_PHOENIX}.is_phoenix_reachable", return_value=reachable),
        patch(f"{LOCAL_PHOENIX}.port_in_use", return_value=port_in_use),
    )


LOCAL_CONFIG = dict(ui_parser_mode="omniparser", enable_tracing=True, tracing_provider="phoenix")


def test_no_warning_when_the_local_phoenix_answers():
    up, port = _local_phoenix(reachable=True)
    with up, port:
        assert _collect(Config(**LOCAL_CONFIG), phoenix_up=False)[0] == []


def test_warns_about_a_port_held_by_something_else():
    up, port = _local_phoenix(port_in_use=True)
    with up, port, patch(f"{LOCAL_PHOENIX}.is_running", return_value=False):
        warnings, _ = _collect(Config(**LOCAL_CONFIG, phoenix_url="http://localhost:7007"))

    assert len(warnings) == 1
    assert "port 7007" in warnings[0].message and "not Phoenix" in warnings[0].message


def test_own_container_that_does_not_answer_is_not_called_a_port_conflict():
    up, port = _local_phoenix(port_in_use=True)
    with up, port, patch(f"{LOCAL_PHOENIX}.is_running", return_value=True):
        warnings, _ = _collect(Config(**LOCAL_CONFIG))

    assert len(warnings) == 1
    assert "not Phoenix" not in warnings[0].message and "docker logs" in warnings[0].message


def test_start_failure_without_a_recorded_reason_points_at_docker():
    up, port = _local_phoenix()
    with up, port:
        warnings, _ = _collect(Config(**LOCAL_CONFIG))

    assert "Docker Desktop is running" in warnings[0].message


def test_warns_with_the_start_failure(monkeypatch):
    from mobile_crawler.infrastructure import phoenix_docker

    monkeypatch.setitem(phoenix_docker._last_start_errors, 6006, "Docker is not available.")
    up, port = _local_phoenix()
    with up, port:
        warnings, _ = _collect(Config(**LOCAL_CONFIG))

    assert len(warnings) == 1
    message = warnings[0].message
    assert "could not be started" in message and "Docker is not available." in message
    assert "start the Phoenix server" not in message


def test_a_failing_check_is_skipped():
    config = Config(ui_parser_mode="boost", enable_tracing=True, tracing_provider="phoenix")
    up, port = _local_phoenix()
    with (
        patch(ADB_DEVICE, new=AsyncMock(side_effect=RuntimeError("adb gone"))),
        up,
        port,
    ):
        warnings = collect_pre_run_warnings(config, "dev-1")

    assert len(warnings) == 1
    assert "Phoenix" in warnings[0].message
