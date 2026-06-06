"""Regression tests for local OmniParser parse timeout handling."""

import requests

from mobile_crawler.domain.crawler_agent.tools.omniparser_client import OmniParserClient
from mobile_crawler.domain.omni_parser_client import OmniParserClient as LegacyOmniParserClient


class _Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {"parsed_content_list": []}

    def json(self):
        return self._payload


class _Config:
    def get(self, key, default=None):
        return {
            "omniparser_local_url": "http://localhost:8000",
            "omniparser_box_threshold": 0.05,
            "omniparser_local_parse_timeout_seconds": 180,
        }.get(key, default)


def test_crawler_agent_local_client_uses_configured_parse_timeout(monkeypatch):
    """Crawler-agent local client should not hardcode the old 30s timeout."""
    calls = []

    def fake_post(url, json, timeout):
        calls.append((url, json, timeout))
        return _Response()

    monkeypatch.setattr(requests, "post", fake_post)

    client = OmniParserClient(
        backend="local",
        local_url="http://localhost:8000",
        local_parse_timeout_seconds=180,
    )
    assert client.parse(b"fake-image") == []

    assert calls[0][0] == "http://localhost:8000/parse/"
    assert calls[0][2] == 180


def test_crawler_agent_local_client_only_falls_back_on_404(monkeypatch):
    """Timed-out /parse/ calls should not be repeated against /parse."""
    calls = []

    def fake_post(url, json, timeout):
        calls.append(url)
        if len(calls) == 1:
            raise requests.exceptions.Timeout("slow parse")
        return _Response()

    monkeypatch.setattr(requests, "post", fake_post)

    client = OmniParserClient(
        backend="local",
        local_url="http://localhost:8000",
        local_parse_timeout_seconds=180,
    )

    try:
        client.parse(b"fake-image")
    except requests.exceptions.Timeout:
        pass

    assert calls == ["http://localhost:8000/parse/"]


def test_legacy_local_client_uses_configured_parse_timeout(monkeypatch):
    """Legacy OmniParser client should use the same configurable local timeout."""
    calls = []

    def fake_post(url, json, timeout):
        calls.append((url, json, timeout))
        return _Response()

    monkeypatch.setattr(requests, "post", fake_post)

    client = LegacyOmniParserClient(_Config())
    monkeypatch.setattr(client, "check_local_available", lambda: True)
    client.set_backend("local")
    assert client.parse(b"fake-image") == []

    assert calls[0][0] == "http://localhost:8000/parse/"
    assert calls[0][2] == 180
