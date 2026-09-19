"""Reads a run's telemetry back from Phoenix or Langfuse, by the run's trace session id."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

import requests

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10
_MAX_ERRORS = 10
_MAX_PAGES = 20


@dataclass
class TelemetrySummary:
    """What a tracing server knows about one run.

    status: ok | unreachable | no_trace_id | not_configured | pending
    """

    status: str
    provider: str | None = None
    trace_count: int | None = None
    span_count: int | None = None
    llm_calls: int | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    total_cost: float | None = None
    avg_latency_ms: float | None = None
    errors: list[str] = field(default_factory=list)
    link: str | None = None
    note: str = ""


class TelemetryClient(Protocol):
    provider: str

    def fetch(self, session_id: str) -> TelemetrySummary: ...


HttpGet = Callable[..., Any]


class LangfuseTelemetryClient:
    """Langfuse public API: GET /api/public/traces?sessionId=... (Basic Auth with the project keys)."""

    provider = "langfuse"

    def __init__(self, host: str, public_key: str, secret_key: str, http_get: HttpGet = requests.get):
        self.host = host.rstrip("/")
        self.public_key = public_key
        self.secret_key = secret_key
        self._get = http_get

    def fetch(self, session_id: str) -> TelemetrySummary:
        traces: list[dict[str, Any]] = []
        page = 1
        while page <= _MAX_PAGES:
            response = self._get(
                f"{self.host}/api/public/traces",
                params={"sessionId": session_id, "limit": 100, "page": page},
                auth=(self.public_key, self.secret_key),
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
            traces.extend(body.get("data", []))
            if page >= int((body.get("meta") or {}).get("totalPages") or 1):
                break
            page += 1

        latencies = [t["latency"] * 1000 for t in traces if t.get("latency") is not None]
        costs = [t["totalCost"] for t in traces if t.get("totalCost") is not None]
        return TelemetrySummary(
            status="ok",
            provider=self.provider,
            trace_count=len(traces),
            total_cost=sum(costs) if costs else None,
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else None,
            link=self._session_link(session_id, traces),
        )

    def _session_link(self, session_id: str, traces: list[dict[str, Any]]) -> str | None:
        # Trace html paths look like /project/<id>/traces/<trace>; reuse the project prefix.
        for trace in traces:
            path = trace.get("htmlPath") or ""
            if path.startswith("/project/"):
                project_prefix = "/".join(path.split("/")[:3])
                return f"{self.host}{project_prefix}/sessions/{session_id}"
        return None


class PhoenixTelemetryClient:
    """Phoenix REST API: GET /v1/projects/{project}/spans, filtered by the session.id attribute."""

    provider = "phoenix"

    def __init__(self, url: str, project: str = "default", http_get: HttpGet = requests.get):
        self.url = url.rstrip("/")
        self.project = project
        self._get = http_get

    def fetch(self, session_id: str) -> TelemetrySummary:
        spans: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(_MAX_PAGES):
            params: dict[str, Any] = {"limit": 1000}
            if cursor:
                params["cursor"] = cursor
            response = self._get(
                f"{self.url}/v1/projects/{self.project}/spans",
                params=params,
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
            spans.extend(s for s in body.get("data", []) if (s.get("attributes") or {}).get("session.id") == session_id)
            cursor = body.get("next_cursor")
            if not cursor:
                break

        llm_spans = [s for s in spans if s.get("span_kind") == "LLM"]
        latencies = [latency for latency in (self._duration_ms(s) for s in llm_spans) if latency is not None]
        errors = [(s.get("status_message") or "error (no message)") for s in spans if s.get("status_code") == "ERROR"][
            :_MAX_ERRORS
        ]
        return TelemetrySummary(
            status="ok",
            provider=self.provider,
            trace_count=len({(s.get("context") or {}).get("trace_id") for s in spans}),
            span_count=len(spans),
            llm_calls=len(llm_spans),
            tokens_input=sum(int(s["attributes"].get("llm.token_count.prompt") or 0) for s in llm_spans),
            tokens_output=sum(int(s["attributes"].get("llm.token_count.completion") or 0) for s in llm_spans),
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else None,
            errors=errors,
            link=self.url,
            note=f"Search for session id {session_id} in the Phoenix UI.",
        )

    @staticmethod
    def _duration_ms(span: dict[str, Any]) -> float | None:
        try:
            start = datetime.fromisoformat(span["start_time"])
            end = datetime.fromisoformat(span["end_time"])
        except (KeyError, TypeError, ValueError):
            return None
        return (end - start).total_seconds() * 1000


def fetch_run_telemetry(trace_id: str | None, client: TelemetryClient | None) -> TelemetrySummary:
    """Fetch a run's telemetry; never raises. Failures come back as a status the report can show."""
    if not trace_id:
        return TelemetrySummary(
            status="no_trace_id",
            note="No trace session id was recorded (run predates telemetry linking or tracing was off).",
        )
    if client is None:
        return TelemetrySummary(status="not_configured", note="Tracing was not enabled or configured for this run.")
    try:
        return client.fetch(trace_id)
    except Exception as e:
        logger.warning("Could not fetch telemetry for %s: %s", trace_id, e)
        return TelemetrySummary(status="unreachable", provider=getattr(client, "provider", None), note=str(e))


def build_telemetry_client_factory(config_manager: Any) -> Callable[[str], TelemetryClient | None]:
    """Map a provider name to a client configured from the app's current tracing settings."""

    def factory(provider: str) -> TelemetryClient | None:
        if provider == "langfuse":
            host = config_manager.get("langfuse_host", "https://cloud.langfuse.com")
            public_key = config_manager.get("langfuse_public_key", "")
            secret_key = config_manager.get("langfuse_secret_key", "")
            if not (host and public_key and secret_key):
                return None
            return LangfuseTelemetryClient(host, public_key, secret_key)
        if provider == "phoenix":
            url = config_manager.get("phoenix_url", "http://localhost:6006")
            project = config_manager.get("phoenix_project_name", "") or "default"
            return PhoenixTelemetryClient(url, project) if url else None
        return None

    return factory
