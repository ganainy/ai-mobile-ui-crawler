"""apply_session_context tags spans with the per-run session id for every tracing provider."""

import sys
import types

import pytest
from opentelemetry import context as otel_context

from mobile_crawler.domain.crawler_agent.agent.utils import tracing_setup


@pytest.fixture
def fake_openinference(monkeypatch):
    """Stand-in for openinference.semconv.trace so the test needs no optional extra."""
    attrs = types.SimpleNamespace(SESSION_ID="session.id", USER_ID="user.id")
    trace_mod = types.ModuleType("openinference.semconv.trace")
    trace_mod.SpanAttributes = attrs
    for name in ("openinference", "openinference.semconv"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, "openinference.semconv.trace", trace_mod)
    return attrs


@pytest.mark.parametrize("provider", ["phoenix", "langfuse"])
def test_session_id_is_applied_for_both_providers(monkeypatch, fake_openinference, provider):
    monkeypatch.setattr(tracing_setup, "_tracing_initialized", True)
    monkeypatch.setattr(tracing_setup, "_tracing_provider", provider)
    monkeypatch.setattr(tracing_setup, "_session_id", "run-7-abcd1234")
    token_ctx = otel_context.get_current()

    tracing_setup.apply_session_context()

    try:
        assert otel_context.get_value("session.id") == "run-7-abcd1234"
    finally:
        otel_context.attach(token_ctx)


def test_nothing_is_applied_when_tracing_is_not_initialized(monkeypatch, fake_openinference):
    monkeypatch.setattr(tracing_setup, "_tracing_initialized", False)
    monkeypatch.setattr(tracing_setup, "_session_id", "run-7-abcd1234")

    tracing_setup.apply_session_context()

    assert otel_context.get_value("session.id") is None
