"""Tests for picking the CLI device: --device when given, else the only connected one."""

from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from mobile_crawler.cli.device_choice import resolve_device
from mobile_crawler.cli.main import cli
from mobile_crawler.infrastructure.device_detection import AndroidDevice, ADBNotFoundError

AVAILABLE = "mobile_crawler.cli.device_choice.DeviceDetection.get_available_devices"


def _devices(*ids):
    return [AndroidDevice(device_id=i, status="device") for i in ids]


def test_explicit_device_is_used_without_asking_adb():
    with patch(AVAILABLE) as available:
        assert resolve_device("dev-9") == "dev-9"
    available.assert_not_called()


def test_single_connected_device_is_picked():
    with patch(AVAILABLE, return_value=_devices("emulator-5554")):
        assert resolve_device(None) == "emulator-5554"


def test_no_device_is_a_usage_error():
    with patch(AVAILABLE, return_value=[]), pytest.raises(click.UsageError, match="No device connected"):
        resolve_device(None)


def test_several_devices_need_device_flag():
    with patch(AVAILABLE, return_value=_devices("a", "b")), pytest.raises(click.UsageError, match=r"\(a, b\).*--device"):
        resolve_device(None)


def test_missing_adb_is_reported():
    with patch(AVAILABLE, side_effect=ADBNotFoundError("adb not found")), pytest.raises(click.ClickException, match="adb not found"):
        resolve_device(None)


def test_portal_status_uses_the_only_device():
    with (
        patch(AVAILABLE, return_value=_devices("dev-1")),
        patch("mobile_crawler.core.portal_actions.check_portal", return_value=("ready", True)) as check,
    ):
        result = CliRunner().invoke(cli, ["a11y-portal", "status"])

    assert result.exit_code == 0
    check.assert_called_once_with("dev-1")


def test_list_apps_uses_the_only_device():
    with (
        patch(AVAILABLE, return_value=_devices("dev-1")),
        patch("mobile_crawler.infrastructure.installed_apps.list_third_party_packages", return_value=[]) as packages,
    ):
        result = CliRunner().invoke(cli, ["list", "apps", "--no-names"])

    assert result.exit_code == 0
    packages.assert_called_once_with("dev-1")


def test_crawl_with_several_devices_and_no_flag_exits_2():
    with patch(AVAILABLE, return_value=_devices("a", "b")):
        result = CliRunner().invoke(cli, ["crawl", "--package", "com.x", "--model", "m"])

    assert result.exit_code == 2
    assert "pick one with --device" in result.output
