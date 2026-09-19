"""Fetching a run's Phoenix / Langfuse telemetry by its trace session id.

The HTTP layer is injected, so responses below are canned from the providers' documented shapes.
"""

import pytest

from mobile_crawler.infrastructure.telemetry_client import (
    LangfuseTelemetryClient,
    PhoenixTelemetryClient,
    fetch_run_telemetry,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeHttp:
    """Records calls and replays responses in order."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, params=None, headers=None, auth=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers, "auth": auth})
        return self.responses.pop(0)


def test_langfuse_summarises_traces_for_the_session():
    http = FakeHttp(
        FakeResponse(
            {
                "data": [
                    {"id": "t1", "latency": 2.0, "totalCost": 0.01, "htmlPath": "/project/p1/traces/t1"},
                    {"id": "t2", "latency": 4.0, "totalCost": 0.02, "htmlPath": "/project/p1/traces/t2"},
                ],
                "meta": {"page": 1, "totalPages": 1},
            }
        )
    )
    client = LangfuseTelemetryClient("https://lf.example", "pk", "sk", http_get=http)

    summary = client.fetch("run-1-abcd1234")

    assert http.calls[0]["url"] == "https://lf.example/api/public/traces"
    assert http.calls[0]["params"]["sessionId"] == "run-1-abcd1234"
    assert http.calls[0]["auth"] == ("pk", "sk")
    assert summary.status == "ok"
    assert summary.provider == "langfuse"
    assert summary.trace_count == 2
    assert summary.total_cost == pytest.approx(0.03)
    assert summary.avg_latency_ms == pytest.approx(3000.0)
    assert summary.link == "https://lf.example/project/p1/sessions/run-1-abcd1234"


def test_langfuse_follows_pagination():
    http = FakeHttp(
        FakeResponse({"data": [{"id": "t1"}], "meta": {"page": 1, "totalPages": 2}}),
        FakeResponse({"data": [{"id": "t2"}], "meta": {"page": 2, "totalPages": 2}}),
    )

    summary = LangfuseTelemetryClient("https://lf.example", "pk", "sk", http_get=http).fetch("s")

    assert summary.trace_count == 2
    assert [c["params"]["page"] for c in http.calls] == [1, 2]


def test_phoenix_summarises_llm_spans_for_the_session_only():
    def span(trace, kind, session, **attrs):
        return {
            "name": "x",
            "span_kind": kind,
            "status_code": attrs.pop("status", "OK"),
            "status_message": attrs.pop("message", ""),
            "start_time": "2026-09-19T10:00:00+00:00",
            "end_time": attrs.pop("end", "2026-09-19T10:00:02+00:00"),
            "context": {"trace_id": trace, "span_id": "s"},
            "attributes": {"session.id": session, **attrs},
        }

    http = FakeHttp(
        FakeResponse(
            {
                "data": [
                    span(
                        "t1",
                        "LLM",
                        "run-1-abcd1234",
                        **{"llm.token_count.prompt": 100, "llm.token_count.completion": 20},
                    ),
                    span(
                        "t1",
                        "LLM",
                        "run-1-abcd1234",
                        status="ERROR",
                        message="429 rate limited",
                        **{"llm.token_count.prompt": 50, "llm.token_count.completion": 0},
                    ),
                    span("t2", "CHAIN", "run-1-abcd1234"),
                    span("t9", "LLM", "someone-elses-session", **{"llm.token_count.prompt": 999}),
                ],
                "next_cursor": None,
            }
        )
    )
    client = PhoenixTelemetryClient("http://localhost:6006", "default", http_get=http)

    summary = client.fetch("run-1-abcd1234")

    assert http.calls[0]["url"] == "http://localhost:6006/v1/projects/default/spans"
    assert summary.status == "ok"
    assert summary.provider == "phoenix"
    assert summary.trace_count == 2
    assert summary.span_count == 3
    assert summary.llm_calls == 2
    assert summary.tokens_input == 150
    assert summary.tokens_output == 20
    assert summary.avg_latency_ms == pytest.approx(2000.0)
    assert summary.errors == ["429 rate limited"]


def test_phoenix_follows_cursor_pagination():
    http = FakeHttp(
        FakeResponse({"data": [], "next_cursor": "abc"}),
        FakeResponse({"data": [], "next_cursor": None}),
    )

    PhoenixTelemetryClient("http://x", "default", http_get=http).fetch("s")

    assert http.calls[1]["params"]["cursor"] == "abc"


def test_unreachable_server_is_reported_not_raised():
    def boom(*args, **kwargs):
        raise ConnectionError("connection refused")

    class Client:
        provider = "phoenix"

        def fetch(self, session_id):
            return PhoenixTelemetryClient("http://x", "default", http_get=boom).fetch(session_id)

    summary = fetch_run_telemetry(trace_id="run-1-x", client=Client())

    assert summary.status == "unreachable"
    assert "connection refused" in summary.note


def test_missing_trace_id_is_reported_without_calling_the_server():
    class Client:
        provider = "langfuse"

        def fetch(self, session_id):
            raise AssertionError("must not be called")

    summary = fetch_run_telemetry(trace_id=None, client=Client())

    assert summary.status == "no_trace_id"


def test_missing_client_means_tracing_was_not_configured():
    summary = fetch_run_telemetry(trace_id="run-1-x", client=None)

    assert summary.status == "not_configured"


def test_server_http_error_is_reported_as_unreachable():
    http = FakeHttp(FakeResponse({}, status_code=401))

    summary = fetch_run_telemetry(
        trace_id="s", client=LangfuseTelemetryClient("https://lf", "pk", "bad", http_get=http)
    )

    assert summary.status == "unreachable"
    assert "401" in summary.note


class FakeConfig:
    def __init__(self, values):
        self.values = values

    def get(self, key, default=None):
        return self.values.get(key, default)


def test_factory_builds_langfuse_client_from_settings():
    from mobile_crawler.infrastructure.telemetry_client import build_telemetry_client_factory

    factory = build_telemetry_client_factory(
        FakeConfig({"langfuse_host": "https://lf.example", "langfuse_public_key": "pk", "langfuse_secret_key": "sk"})
    )

    client = factory("langfuse")

    assert isinstance(client, LangfuseTelemetryClient)
    assert (client.host, client.public_key, client.secret_key) == ("https://lf.example", "pk", "sk")


def test_factory_builds_phoenix_client_from_settings():
    from mobile_crawler.infrastructure.telemetry_client import build_telemetry_client_factory

    factory = build_telemetry_client_factory(
        FakeConfig({"phoenix_url": "http://phx:6006", "phoenix_project_name": "crawler"})
    )

    client = factory("phoenix")

    assert isinstance(client, PhoenixTelemetryClient)
    assert (client.url, client.project) == ("http://phx:6006", "crawler")


def test_factory_returns_none_for_unknown_provider_or_missing_langfuse_keys():
    from mobile_crawler.infrastructure.telemetry_client import build_telemetry_client_factory

    factory = build_telemetry_client_factory(FakeConfig({"langfuse_host": "https://lf.example"}))

    assert factory("langfuse") is None
    assert factory("datadog") is None
