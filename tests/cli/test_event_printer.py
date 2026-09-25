"""Tests for the readable (pretty) crawl output."""

import io
import json
import sys

from mobile_crawler.cli.event_printer import PrettyEventListener, format_duration
from mobile_crawler.domain.models import ActionResult


def _listener(log_level="INFO"):
    out = io.StringIO()
    return PrettyEventListener(log_level, out=out, color=False), out


def _lines(out):
    """Printed lines without their HH:MM:SS timestamp."""
    return [line.split(" ", 1)[1] for line in out.getvalue().splitlines() if line.strip()]


class TestFormatDuration:
    def test_scales_units(self):
        assert format_duration(230) == "230 ms"
        assert format_duration(4100) == "4.1 s"
        assert format_duration(252_000) == "4m 12s"


class TestDebugLog:
    def test_message_gets_a_level_label_and_no_json(self):
        listener, out = _listener()

        listener.on_debug_log(1, 0, "Traffic capture started", "INFO")

        assert _lines(out) == ["info   Traffic capture started"]

    def test_levels_below_the_minimum_are_dropped(self):
        listener, out = _listener("INFO")

        listener.on_debug_log(1, 0, "Using accessibility tree (17 nodes)", "DEBUG")

        assert out.getvalue() == ""

    def test_stdout_and_stderr_mirrors_are_dropped(self):
        """They were already echoed to the terminal when printed."""
        listener, out = _listener("DEBUG")

        listener.on_debug_log(1, 0, "[stdout] Credentials disabled in config", "DEBUG")
        listener.on_debug_log(1, 0, "[stderr] Both GOOGLE_API_KEY and GEMINI_API_KEY are set.", "DEBUG")

        assert out.getvalue() == ""

    def test_known_noise_is_dropped(self):
        listener, out = _listener("DEBUG")

        listener.on_debug_log(1, 0, "Attempting to import module: llama_index.llms.google_genai", "DEBUG")

        assert out.getvalue() == ""

    def test_ansi_codes_are_stripped(self):
        listener, out = _listener()

        listener.on_debug_log(1, 0, "\x1b[36m📋 Manager response:\x1b[0m", "INFO")

        assert _lines(out) == ["info   📋 Manager response:"]

    def test_continuation_lines_are_indented_under_the_message(self):
        listener, out = _listener()

        listener.on_debug_log(1, 0, "<plan>\n1. Click Join\n</plan>", "INFO")

        lines = out.getvalue().splitlines()
        assert lines[0].endswith("info   <plan>")
        assert lines[1] == " " * 16 + "1. Click Join"


class TestEvents:
    def test_step_start_is_a_separator(self):
        listener, out = _listener()

        listener.on_step_started(1, 3)

        assert "── Step 3 ─" in out.getvalue()

    def test_successful_and_failed_actions(self):
        listener, out = _listener()

        listener.on_action_executed(1, 1, 0, ActionResult(True, "click", "Join for free", duration_ms=230))
        listener.on_action_executed(
            1, 1, 1, ActionResult(False, "type", "email", duration_ms=50, error_message="no field")
        )

        assert _lines(out) == [
            "action ✓ click Join for free (230 ms)",
            "action ✗ type email (50 ms): no field",
        ]

    def test_ai_response_is_a_one_line_summary(self):
        listener, out = _listener()

        listener.on_ai_response_received(
            1,
            1,
            {"call_type": "manager", "latency_ms": 2800, "tokens_input": 5120, "tokens_output": 88, "response": "x" * 5000},
        )

        assert _lines(out) == ["ai     manager response (2.8 s, 5,120 in / 88 out tokens)"]

    def test_failed_ai_response_shows_the_error(self):
        listener, out = _listener()

        listener.on_ai_response_received(1, 1, {"call_type": "executor", "success": False, "error_message": "timeout"})

        assert _lines(out) == ["ai     executor response failed: timeout"]

    def test_ai_request_is_summarized_only_at_debug(self):
        request = {"user_prompt": json.dumps({"text": "abc", "screenshot": "A" * 999}), "ui_elements": [{}, {}]}
        info, info_out = _listener("INFO")
        debug, debug_out = _listener("DEBUG")

        info.on_ai_request_sent(1, 1, request)
        debug.on_ai_request_sent(1, 1, request)

        assert info_out.getvalue() == ""
        assert _lines(debug_out) == ["ai     Request sent: 2 UI elements, 3 prompt characters"]

    def test_crawl_completed(self):
        listener, out = _listener()

        listener.on_crawl_completed(188, 30, 252_000, "Step limit reached")

        assert "Run 188 finished: 30 steps in 4m 12s" in out.getvalue()
        assert "Step limit reached" in out.getvalue()


class TestOutputStream:
    def test_writes_to_the_stream_that_was_stdout_at_creation(self, monkeypatch):
        """The crawl swaps stdout for a capturing stream; writing there would log every line twice."""
        real = io.StringIO()
        monkeypatch.setattr(sys, "stdout", real)
        listener = PrettyEventListener(color=False)
        swapped = io.StringIO()
        monkeypatch.setattr(sys, "stdout", swapped)

        listener.on_crawl_started(1, "com.example")

        assert "Run 1 started: com.example" in real.getvalue()
        assert swapped.getvalue() == ""

    def test_unencodable_characters_are_replaced(self):
        raw = io.BytesIO()
        out = io.TextIOWrapper(raw, encoding="cp1252")
        listener = PrettyEventListener(out=out, color=False)

        listener.on_debug_log(1, 0, "🚀 Running", "INFO")

        assert b"? Running" in raw.getvalue()
