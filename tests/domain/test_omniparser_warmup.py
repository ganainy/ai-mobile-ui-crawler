"""Tests for OmniParser warm-up helpers."""

from mobile_crawler.domain.omniparser_warmup import create_mock_screenshot, warm_up_remote_omniparser


def test_create_mock_screenshot_returns_jpeg_bytes():
    screenshot = create_mock_screenshot()

    assert screenshot.startswith(b"\xff\xd8")
    assert len(screenshot) > 1000


def test_warm_up_remote_omniparser_uses_replicate_client(monkeypatch):
    calls = {}

    class FakeClient:
        def __init__(self, **kwargs):
            calls["kwargs"] = kwargs

        def parse(self, image_bytes):
            calls["image_bytes"] = image_bytes
            return [{"content": "Start"}]

    monkeypatch.setattr(
        "mobile_crawler.domain.crawler_agent.tools.omniparser_client.OmniParserClient",
        FakeClient,
    )

    elements = warm_up_remote_omniparser(api_key="replicate-key", box_threshold=0.2)

    assert elements == [{"content": "Start"}]
    assert calls["kwargs"] == {
        "backend": "replicate",
        "api_key": "replicate-key",
        "box_threshold": 0.2,
    }
    assert calls["image_bytes"].startswith(b"\xff\xd8")
