"""Tests for the `a11y-portal status|enable|install` CLI commands."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mobile_crawler.cli.main import cli

ACTIONS = "mobile_crawler.core.portal_actions"


@pytest.mark.parametrize(("command", "action"), [("status", "check_portal"), ("enable", "fix_portal"), ("install", "install_portal")])
def test_ready_prints_the_status_and_exits_0(command, action):
    with patch(f"{ACTIONS}.{action}", return_value=("Portal 0.7.25 is ready", True)) as run:
        result = CliRunner().invoke(cli, ["a11y-portal", command, "--device", "dev-1"])

    assert result.exit_code == 0
    assert "Portal 0.7.25 is ready" in result.output
    run.assert_called_once_with("dev-1")


def test_not_ready_prints_the_manual_steps_and_exits_1():
    with patch(f"{ACTIONS}.check_portal", return_value=("Portal is installed but its accessibility service is off", False)):
        result = CliRunner().invoke(cli, ["a11y-portal", "status", "--device", "dev-1"])

    assert result.exit_code == 1
    assert "accessibility service is off" in result.output
    assert "Settings > Accessibility" in result.output
