"""The blocking Portal helpers used by the Settings panel."""

from unittest.mock import AsyncMock

import pytest

from mobile_crawler.domain.crawler_agent import portal
from mobile_crawler.ui import portal_actions


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
