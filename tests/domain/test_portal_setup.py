"""Tests for the pinned Portal download and the read-only Portal status check."""

import hashlib
from unittest.mock import AsyncMock, Mock

import pytest

from mobile_crawler.domain.crawler_agent import portal


def _fake_response(payload: bytes):
    response = Mock()
    response.raise_for_status = Mock()
    response.iter_content = Mock(return_value=[payload])
    return response


@pytest.fixture
def cache(tmp_path, monkeypatch):
    path = tmp_path / "portal" / "portal.apk"
    monkeypatch.setattr(portal, "_portal_cache_path", lambda: path)
    return path


def test_download_verifies_sha256_and_caches(cache, monkeypatch):
    payload = b"apk-bytes"
    monkeypatch.setattr(portal, "PORTAL_APK_SHA256", hashlib.sha256(payload).hexdigest())
    get = Mock(return_value=_fake_response(payload))
    monkeypatch.setattr(portal.requests, "get", get)

    with portal.download_portal_apk() as first:
        assert open(first, "rb").read() == payload
    with portal.download_portal_apk():
        pass

    assert get.call_count == 1  # second use came from the cache


def test_download_rejects_a_file_that_does_not_match_the_pin(cache, monkeypatch):
    monkeypatch.setattr(portal, "PORTAL_APK_SHA256", hashlib.sha256(b"expected").hexdigest())
    monkeypatch.setattr(portal.requests, "get", Mock(return_value=_fake_response(b"tampered")))

    with pytest.raises(RuntimeError, match="SHA-256"), portal.download_portal_apk():
        pass

    assert not cache.exists()


def test_corrupt_cached_file_is_downloaded_again(cache, monkeypatch):
    payload = b"good"
    monkeypatch.setattr(portal, "PORTAL_APK_SHA256", hashlib.sha256(payload).hexdigest())
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"corrupt")
    get = Mock(return_value=_fake_response(payload))
    monkeypatch.setattr(portal.requests, "get", get)

    with portal.download_portal_apk() as path:
        assert open(path, "rb").read() == payload
    assert get.call_count == 1


def test_version_tuple_orders_versions_numerically():
    assert portal._version_tuple("0.7.25") > portal._version_tuple("0.7.9")
    assert portal._version_tuple("v1.0.0") > portal._version_tuple("0.99.99")


def _device(packages, version_output, services):
    device = Mock()
    device.list_packages = AsyncMock(return_value=packages)
    device.shell = AsyncMock(side_effect=[version_output, services] if packages else [services])
    return device


@pytest.mark.asyncio
async def test_status_reports_missing_portal():
    status = await portal.get_portal_status(_device([], "", "null"))
    assert not status.installed and not status.ready
    assert "not installed" in status.describe()


@pytest.mark.asyncio
async def test_status_reports_installed_but_service_off():
    device = _device([portal.PORTAL_PACKAGE_NAME], 'Row: 0 result={"status":"success","result":"0.7.25"}', "null")
    status = await portal.get_portal_status(device)
    assert status.installed and not status.accessibility_enabled and not status.ready
    assert "accessibility service is off" in status.describe()


@pytest.mark.asyncio
async def test_status_reports_ready():
    device = _device(
        [portal.PORTAL_PACKAGE_NAME],
        'Row: 0 result={"status":"success","result":"0.7.25"}',
        portal.A11Y_SERVICE_NAME,
    )
    status = await portal.get_portal_status(device)
    assert status.ready and status.version == "0.7.25"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current", "written"),
    [
        ("null", portal.A11Y_SERVICE_NAME),
        ("com.other/.Svc", f"com.other/.Svc:{portal.A11Y_SERVICE_NAME}"),
        (portal.A11Y_SERVICE_NAME, portal.A11Y_SERVICE_NAME),
    ],
)
async def test_enable_keeps_other_accessibility_services(current, written):
    device = AsyncMock()
    device.shell = AsyncMock(side_effect=[current, "", ""])

    await portal.enable_portal_accessibility(device)

    assert device.shell.await_args_list[1].args[0] == f"settings put secure enabled_accessibility_services {written}"
