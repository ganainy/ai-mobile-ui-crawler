"""The blocking Portal helpers used by the Settings panel."""

from unittest.mock import AsyncMock

import pytest

from mobile_crawler.domain.crawler_agent import portal
from mobile_crawler.core import portal_actions


@pytest.fixture(autouse=True)
def _fake_device(monkeypatch):
    from async_adbutils import adb

    monkeypatch.setattr(adb, "device", AsyncMock(return_value=object()))


def test_check_reports_the_status_text_and_readiness(monkeypatch):
    status = portal.PortalStatus(installed=True, version="0.7.25", accessibility_enabled=True)
    monkeypatch.setattr(portal, "get_portal_status", AsyncMock(return_value=status))

    assert portal_actions.check_portal("dev") == ("Portal 0.7.25 is ready", True)


def test_check_reports_a_failure_instead_of_raising(monkeypatch):
    monkeypatch.setattr(portal, "get_portal_status", AsyncMock(side_effect=RuntimeError("device offline")))

    text, ready = portal_actions.check_portal("dev")

    assert not ready and "device offline" in text


def test_install_then_reports_the_new_status(monkeypatch):
    monkeypatch.setattr(portal, "setup_portal", AsyncMock(return_value=True))
    status = portal.PortalStatus(installed=True, version="0.7.25", accessibility_enabled=True)
    monkeypatch.setattr(portal, "get_portal_status", AsyncMock(return_value=status))

    assert portal_actions.install_portal("dev") == ("Portal 0.7.25 is ready", True)


def test_failed_install_explains_what_to_do(monkeypatch):
    monkeypatch.setattr(portal, "setup_portal", AsyncMock(return_value=False))

    text, ready = portal_actions.install_portal("dev")

    assert not ready and "accept it on the phone" in text


def test_enable_turns_the_service_on_and_reports_the_new_status(monkeypatch):
    enable = AsyncMock()
    monkeypatch.setattr(portal, "enable_portal_accessibility", enable)
    monkeypatch.setattr(portal, "wait_for_portal_service", AsyncMock())
    monkeypatch.setattr(portal, "toggle_overlay", AsyncMock())
    status = portal.PortalStatus(installed=True, version="0.7.25", accessibility_enabled=True)
    monkeypatch.setattr(portal, "get_portal_status", AsyncMock(return_value=status))

    assert portal_actions.enable_portal("dev") == ("Portal 0.7.25 is ready", True)
    enable.assert_awaited_once()


def test_enable_that_did_not_take_says_to_do_it_by_hand(monkeypatch):
    monkeypatch.setattr(portal, "enable_portal_accessibility", AsyncMock())
    monkeypatch.setattr(portal, "wait_for_portal_service", AsyncMock())
    monkeypatch.setattr(portal, "toggle_overlay", AsyncMock())
    status = portal.PortalStatus(installed=True, version="0.7.25", accessibility_enabled=False)
    monkeypatch.setattr(portal, "get_portal_status", AsyncMock(return_value=status))

    text, ready = portal_actions.enable_portal("dev")

    assert not ready and "by hand" in text


@pytest.mark.parametrize(
    ("installed", "enabled", "expected"),
    [(True, True, "none"), (True, False, "enable"), (False, False, "install")],
)
def test_fix_does_the_least_needed(monkeypatch, installed, enabled, expected):
    status = portal.PortalStatus(installed=installed, version="0.7.25", accessibility_enabled=enabled)
    monkeypatch.setattr(portal, "get_portal_status", AsyncMock(return_value=status))
    calls = []
    monkeypatch.setattr(portal_actions, "enable_portal", lambda d: calls.append("enable") or ("ok", True))
    monkeypatch.setattr(portal_actions, "install_portal", lambda d: calls.append("install") or ("ok", True))

    portal_actions.fix_portal("dev")

    assert calls == ([] if expected == "none" else [expected])


def test_manual_steps_say_the_cloud_options_are_not_needed():
    steps = portal_actions.PORTAL_MANUAL_STEPS
    assert "Settings > Accessibility > Installed apps" in steps
    assert "Allow restricted settings" in steps
    assert "API Key" in steps and "Not needed" in steps
