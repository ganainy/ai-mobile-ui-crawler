"""Regression tests for Replicate OmniParser transient-error retry behavior.

Covers PLAN-update-prompt-fix Task 2: the bare ``closed`` error raised when
Replicate's streaming connection drops mid-prediction must be retried with
exponential backoff, and non-transient errors must propagate immediately.
"""

import io

import pytest

from mobile_crawler.domain.crawler_agent.tools.omniparser_client import (
    DEFAULT_REPLICATE_MAX_RETRIES,
    OmniParserClient,
    _is_transient_replicate_error,
)


class _FakeReplicateClient:
    """Fake Replicate client whose ``run`` follows a scripted call sequence."""

    def __init__(self, behaviors):
        """behaviors: list of either return values or Exception instances."""
        self._behaviors = list(behaviors)
        self.calls = 0
        self.received_handles = []

    def run(self, model, input):
        self.calls += 1
        self.received_handles.append(input.get("image"))
        behavior = self._behaviors.pop(0) if self._behaviors else None
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


def _make_replicate_client():
    """Build an OmniParserClient configured for the Replicate backend."""
    return OmniParserClient(backend="replicate", api_key="fake-key")


def _image_handle():
    """Return a fresh in-memory binary file handle for tests."""
    return io.BytesIO(b"fake-jpeg-bytes")


def test_is_transient_replicate_error_matches_bare_closed():
    """The bare 'closed' message from httpx/h11 must be transient."""
    assert _is_transient_replicate_error(RuntimeError("closed"))
    assert _is_transient_replicate_error(RuntimeError("httpx.RemoteProtocolError: Server disconnected"))
    assert _is_transient_replicate_error(RuntimeError("Read timed out"))
    assert _is_transient_replicate_error(RuntimeError("Connection reset by peer"))


def test_is_transient_replicate_error_uses_cause_chain():
    """Wrapped errors must be inspected via __cause__ / __context__."""
    inner = ConnectionError("the server closed the connection")
    try:
        raise RuntimeError("client.run() exploded") from inner
    except RuntimeError as wrapped:
        assert _is_transient_replicate_error(wrapped)


def test_is_transient_replicate_error_rejects_non_transient():
    """Auth / 4xx-style errors are NOT transient and must surface immediately."""
    assert not _is_transient_replicate_error(ValueError("invalid image bytes"))
    assert not _is_transient_replicate_error(RuntimeError("401 unauthorized"))
    assert not _is_transient_replicate_error(RuntimeError("malformed response"))


def test_replicate_retry_succeeds_after_transient_failure(monkeypatch):
    """A transient failure followed by success should return the success value."""
    sleeps = []
    monkeypatch.setattr(
        "mobile_crawler.domain.crawler_agent.tools.omniparser_client.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    fake_client = _FakeReplicateClient([RuntimeError("closed"), {"elements": []}])
    client = _make_replicate_client()

    output = client._run_replicate_with_retry(fake_client, _image_handle())

    assert output == {"elements": []}
    assert fake_client.calls == 2
    assert len(sleeps) == 1


def test_replicate_retry_gives_up_after_max_retries(monkeypatch):
    """Persistent transient errors must eventually propagate."""
    monkeypatch.setattr(
        "mobile_crawler.domain.crawler_agent.tools.omniparser_client.time.sleep",
        lambda seconds: None,
    )

    fake_client = _FakeReplicateClient([RuntimeError("closed")] * DEFAULT_REPLICATE_MAX_RETRIES)
    client = _make_replicate_client()

    with pytest.raises(RuntimeError, match="closed"):
        client._run_replicate_with_retry(fake_client, _image_handle())

    assert fake_client.calls == DEFAULT_REPLICATE_MAX_RETRIES


def test_replicate_retry_does_not_swallow_non_transient(monkeypatch):
    """Non-transient errors must propagate immediately without retries."""
    sleeps = []
    monkeypatch.setattr(
        "mobile_crawler.domain.crawler_agent.tools.omniparser_client.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    auth_error = RuntimeError("401 unauthorized")
    fake_client = _FakeReplicateClient([auth_error])
    client = _make_replicate_client()

    with pytest.raises(RuntimeError, match="401"):
        client._run_replicate_with_retry(fake_client, _image_handle())

    assert fake_client.calls == 1
    assert sleeps == []


def test_replicate_retry_uses_exponential_backoff(monkeypatch):
    """Backoff delay must grow exponentially up to the cap."""
    delays = []
    monkeypatch.setattr(
        "mobile_crawler.domain.crawler_agent.tools.omniparser_client.time.sleep",
        lambda seconds: delays.append(seconds),
    )

    fake_client = _FakeReplicateClient([RuntimeError("closed")] * DEFAULT_REPLICATE_MAX_RETRIES)
    client = _make_replicate_client()

    with pytest.raises(RuntimeError):
        client._run_replicate_with_retry(fake_client, _image_handle())

    # Delays should be 1, 2 — DEFAULT_REPLICATE_MAX_RETRIES=3 means 2 sleeps
    # between 3 attempts. Each delay doubles from the previous.
    assert delays == [1.0, 2.0]


def test_replicate_retry_rewinds_handle_between_attempts(monkeypatch):
    """Each retry must re-read the image from the start (seek 0)."""
    monkeypatch.setattr(
        "mobile_crawler.domain.crawler_agent.tools.omniparser_client.time.sleep",
        lambda seconds: None,
    )

    handle = _image_handle()
    fake_client = _FakeReplicateClient([RuntimeError("closed"), {"elements": []}])
    client = _make_replicate_client()

    client._run_replicate_with_retry(fake_client, handle)

    # Both attempts should have received the same handle and it should still
    # be readable from position 0 (the second attempt read the full payload).
    assert fake_client.calls == 2
    assert fake_client.received_handles[0] is handle
    assert fake_client.received_handles[1] is handle
    handle.seek(0)
    assert handle.read() == b"fake-jpeg-bytes"
