"""Tests for installed third-party package enumeration."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from mobile_crawler.infrastructure.installed_apps import (
    is_package_installed,
    is_valid_package_name,
    list_third_party_packages,
    parse_package_list,
)


class TestIsValidPackageName:
    @pytest.mark.parametrize("name", ["com.example.app", "com.example_test.app", "org.a1.b2"])
    def test_valid(self, name):
        assert is_valid_package_name(name) is True

    @pytest.mark.parametrize("name", ["", "example", "Com.example.app", "com..app", "1com.app", "com.example.app;rm"])
    def test_invalid(self, name):
        assert is_valid_package_name(name) is False


class TestParsePackageList:
    def test_parses_sorts_and_drops_invalid(self):
        raw = "package:com.zeta.app\r\npackage:com.alpha.app\nWARNING: junk\npackage:Bad\n\n"
        assert parse_package_list(raw) == ["com.alpha.app", "com.zeta.app"]

    def test_empty(self):
        assert parse_package_list("") == []


class TestListThirdPartyPackages:
    @patch("mobile_crawler.infrastructure.installed_apps.subprocess.run")
    def test_runs_pm_list_packages_minus_3_on_device(self, mock_run):
        mock_run.return_value = Mock(returncode=0, stdout="package:com.b.app\npackage:com.a.app\n", stderr="")

        assert list_third_party_packages("emulator-5554") == ["com.a.app", "com.b.app"]
        args = mock_run.call_args.args[0]
        assert args == ["adb", "-s", "emulator-5554", "shell", "pm", "list", "packages", "-3"]

    @patch("mobile_crawler.infrastructure.installed_apps.subprocess.run")
    def test_nonzero_exit_raises_with_adb_output(self, mock_run):
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="error: device 'x' not found")

        with pytest.raises(RuntimeError, match="device 'x' not found"):
            list_third_party_packages("x")

    @patch("mobile_crawler.infrastructure.installed_apps.subprocess.run")
    def test_timeout_raises_runtime_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=60)

        with pytest.raises(RuntimeError):
            list_third_party_packages("x")


class TestIsPackageInstalled:
    @patch("mobile_crawler.infrastructure.installed_apps.subprocess.run")
    def test_installed_package_has_a_pm_path(self, mock_run):
        mock_run.return_value = Mock(returncode=0, stdout="package:/data/app/com.a.app/base.apk\n", stderr="")

        assert is_package_installed("emulator-5554", "com.a.app") is True
        assert mock_run.call_args.args[0] == ["adb", "-s", "emulator-5554", "shell", "pm", "path", "com.a.app"]

    @patch("mobile_crawler.infrastructure.installed_apps.subprocess.run")
    def test_missing_package_is_not_installed(self, mock_run):
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="")

        assert is_package_installed("emulator-5554", "com.missing.app") is False

    @patch("mobile_crawler.infrastructure.installed_apps.subprocess.run")
    def test_adb_error_raises_instead_of_reporting_not_installed(self, mock_run):
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="error: device 'x' not found")

        with pytest.raises(RuntimeError, match="device 'x' not found"):
            is_package_installed("x", "com.a.app")

    @patch("mobile_crawler.infrastructure.installed_apps.subprocess.run")
    def test_timeout_raises_runtime_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=30)

        with pytest.raises(RuntimeError):
            is_package_installed("x", "com.a.app")
