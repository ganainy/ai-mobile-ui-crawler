"""OTel span processor that collects token counts and LLM latency for the stats dashboard."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

try:
    from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    SpanProcessor = object  # fallback base


@dataclass
class SpanStats:
    """Accumulated token and latency stats collected from OTel LLM spans."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    llm_latencies_ms: list = field(default_factory=list)

    def record_llm_span(self, input_tokens: int, output_tokens: int, duration_ms: float) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        if duration_ms > 0:
            self.llm_latencies_ms.append(duration_ms)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def avg_latency_ms(self) -> float:
        if not self.llm_latencies_ms:
            return 0.0
        return sum(self.llm_latencies_ms) / len(self.llm_latencies_ms)

    def reset(self) -> None:
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.llm_latencies_ms.clear()


class StatsCollectorSpanProcessor(SpanProcessor):
    """OTel SpanProcessor that extracts token counts and latency from LLM spans.

    Registered alongside any other processors (Phoenix, Langfuse) on the same
    TracerProvider. Reads OpenInference semantic convention attributes set by
    the LlamaIndex instrumentor:
      - llm.token_count.prompt   → input tokens
      - llm.token_count.completion → output tokens
      - span duration            → LLM call latency

    Thread-safe; designed to be read from the UI thread via get_stats().
    """

    def __init__(self) -> None:
        self._stats = SpanStats()
        self._lock = threading.Lock()

    def on_start(self, span, parent_context=None) -> None:  # noqa: ARG002
        pass

    def on_end(self, span: ReadableSpan) -> None:
        if not OTEL_AVAILABLE:
            return
        attrs = span.attributes or {}

        # Only process LLM spans (identified by presence of token count attributes)
        input_tokens = attrs.get("llm.token_count.prompt", 0) or 0
        output_tokens = attrs.get("llm.token_count.completion", 0) or 0
        if input_tokens == 0 and output_tokens == 0:
            return

        # Span duration in ms (start/end times are in nanoseconds)
        duration_ms = 0.0
        if span.start_time and span.end_time:
            duration_ms = (span.end_time - span.start_time) / 1_000_000

        with self._lock:
            self._stats.record_llm_span(int(input_tokens), int(output_tokens), duration_ms)

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # noqa: ARG002
        return True

    def get_stats(self) -> SpanStats:
        """Return a snapshot of current accumulated stats (thread-safe)."""
        with self._lock:
            snapshot = SpanStats(
                total_input_tokens=self._stats.total_input_tokens,
                total_output_tokens=self._stats.total_output_tokens,
                llm_latencies_ms=list(self._stats.llm_latencies_ms),
            )
        return snapshot

    def reset(self) -> None:
        """Reset all accumulated stats (call at crawl start)."""
        with self._lock:
            self._stats.reset()
