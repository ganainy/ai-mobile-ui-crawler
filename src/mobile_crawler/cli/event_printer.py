"""Human-readable crawl output for a terminal: one short, aligned line per event instead of JSON.

`crawl --format pretty` (the default when stdout is a terminal) uses this; `--format json` keeps
the JSON event stream for scripts.
"""

import json
import sys
from datetime import datetime
from typing import Any, TextIO

import click

from mobile_crawler.core.crawler_event_listener import CrawlerEventListener
from mobile_crawler.core.log_cleaner import LogCleaner
from mobile_crawler.domain.models import ActionResult

LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

# label, click.style kwargs
_LEVEL_STYLES: dict[str, tuple[str, dict[str, Any]]] = {
    "DEBUG": ("debug", {"dim": True}),
    "INFO": ("info", {}),
    "WARNING": ("warn", {"fg": "yellow"}),
    "ERROR": ("error", {"fg": "red", "bold": True}),
    "CRITICAL": ("error", {"fg": "red", "bold": True}),
}
_LABEL_WIDTH = 6
_INDENT = " " * (len("00:00:00 ") + _LABEL_WIDTH + 1)

# Lines the crawl mirrors from stdout/stderr were already echoed to the terminal as they were printed.
_MIRROR_PREFIXES = ("[stdout]", "[stderr]")


def format_duration(ms: float) -> str:
    """230 ms, 4.1 s, 4m 12s."""
    if ms < 1000:
        return f"{ms:.0f} ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, seconds = divmod(int(round(seconds)), 60)
    return f"{minutes}m {seconds:02d}s"


class PrettyEventListener(CrawlerEventListener):
    """Prints crawl events as readable, colored lines.

    Writes to the stream that was stdout when it was created: the crawl later swaps stdout for a
    capturing stream, and output written there would be logged back as a debug_log event.
    """

    def __init__(self, log_level: str = "INFO", out: TextIO | None = None, color: bool | None = None) -> None:
        self._out = out or sys.stdout
        self._color = self._isatty() if color is None else color
        self._min_log_level = LOG_LEVELS.get(log_level.upper(), 20)
        self._cleaner = LogCleaner()

    # -- output helpers ------------------------------------------------------------------

    def _isatty(self) -> bool:
        try:
            return self._out.isatty()
        except Exception:
            return False

    def _style(self, text: str, **style: Any) -> str:
        return click.style(text, **style) if self._color and style else text

    def _shows(self, level: str) -> bool:
        return LOG_LEVELS.get(level.upper(), 20) >= self._min_log_level

    def _write(self, text: str) -> None:
        try:
            self._out.write(text + "\n")
        except UnicodeEncodeError:
            encoding = getattr(self._out, "encoding", None) or "ascii"
            self._out.write(text.encode(encoding, errors="replace").decode(encoding) + "\n")
        self._out.flush()

    def _line(self, label: str, message: str, **style: Any) -> None:
        """`HH:MM:SS label  message`, continuation lines indented under the message."""
        timestamp = self._style(datetime.now().strftime("%H:%M:%S"), dim=True)
        label_text = self._style(label.ljust(_LABEL_WIDTH), **style)
        first, *rest = message.splitlines() or [""]
        body_style = {"dim": True} if style.get("dim") else {k: v for k, v in style.items() if k == "fg"}
        lines = [f"{timestamp} {label_text} {self._style(first, **body_style)}"]
        lines += [_INDENT + self._style(line, **body_style) if line.strip() else "" for line in rest]
        self._write("\n".join(lines))

    # -- run lifecycle -------------------------------------------------------------------

    def on_crawl_started(self, run_id: int, target_package: str) -> None:
        self._line("run", f"Run {run_id} started: {target_package}", fg="cyan", bold=True)

    def on_state_changed(self, run_id: int, old_state: str, new_state: str) -> None:
        if self._shows("DEBUG"):
            self._line("debug", f"State: {old_state} -> {new_state}", dim=True)

    def on_crawl_completed(self, run_id: int, total_steps: int, duration_ms: float, reason: str) -> None:
        self._write("")
        self._line(
            "run",
            f"Run {run_id} finished: {total_steps} steps in {format_duration(duration_ms)}\n{reason}",
            fg="green",
            bold=True,
        )

    def on_error(self, run_id: int | None, step_number: int | None, error: Exception) -> None:
        where = f"Step {step_number}: " if step_number else ""
        self._line("error", f"{where}{error}", fg="red", bold=True)

    # -- steps ---------------------------------------------------------------------------

    def on_step_started(self, run_id: int, step_number: int) -> None:
        self._write("")
        self._write(self._style(f"── Step {step_number} " + "─" * 40, fg="cyan", bold=True))

    def on_step_completed(self, run_id: int, step_number: int, actions_count: int, duration_ms: float) -> None:
        noun = "action" if actions_count == 1 else "actions"
        self._line("step", f"Step {step_number} done: {actions_count} {noun} in {format_duration(duration_ms)}", dim=True)

    def on_screenshot_captured(self, run_id: int, step_number: int, screenshot_path: str) -> None:
        if self._shows("DEBUG"):
            self._line("debug", f"Screenshot saved: {screenshot_path}", dim=True)

    def on_screenshot_timing(self, run_id: int, step_number: int, duration_ms: float) -> None:
        if self._shows("DEBUG"):
            self._line("debug", f"Screenshot took {format_duration(duration_ms)}", dim=True)

    def on_screen_processed(
        self, run_id: int, step_number: int, screen_id: int, is_new: bool, visit_count: int, total_screens: int
    ) -> None:
        if is_new:
            self._line("screen", f"New screen #{screen_id} ({total_screens} found so far)", fg="magenta")
        else:
            self._line("screen", f"Screen #{screen_id} again, visit {visit_count} ({total_screens} found so far)", dim=True)

    # -- AI and actions ------------------------------------------------------------------

    def on_ai_request_sent(self, run_id: int, step_number: int, request_data: dict[str, Any]) -> None:
        if not self._shows("DEBUG"):
            return
        elements = len(request_data.get("ui_elements") or [])
        prompt_chars = len(_prompt_text(request_data.get("user_prompt")))
        self._line("ai", f"Request sent: {elements} UI elements, {prompt_chars:,} prompt characters", dim=True)

    def on_ai_response_received(self, run_id: int, step_number: int, response_data: dict[str, Any]) -> None:
        details = []
        if response_data.get("latency_ms") is not None:
            details.append(format_duration(response_data["latency_ms"]))
        tokens_in, tokens_out = response_data.get("tokens_input"), response_data.get("tokens_output")
        if tokens_in is not None or tokens_out is not None:
            details.append(f"{tokens_in or 0:,} in / {tokens_out or 0:,} out tokens")
        if response_data.get("retry_count"):
            details.append(f"{response_data['retry_count']} retries")
        call_type = response_data.get("call_type") or "AI"
        summary = f"{call_type} response" + (f" ({', '.join(details)})" if details else "")
        if response_data.get("loop_detected"):
            summary += "; loop detected"
        if response_data.get("success", True) is False:
            error = response_data.get("error_message") or "unknown error"
            self._line("ai", f"{summary} failed: {error}", fg="yellow")
        else:
            self._line("ai", summary, fg="blue")

    def on_action_executed(self, run_id: int, step_number: int, action_index: int, result: ActionResult) -> None:
        target = f" {result.target}" if result.target else ""
        text = f"{result.action_type}{target} ({format_duration(result.duration_ms)})"
        if result.success:
            self._line("action", f"✓ {text}", fg="green")
        else:
            self._line("action", f"✗ {text}: {result.error_message or 'failed'}", fg="red")

    # -- log lines -----------------------------------------------------------------------

    def on_debug_log(self, run_id: int, step_number: int, message: str, level: str = "INFO") -> None:
        if not self._shows(level) or message.lstrip().startswith(_MIRROR_PREFIXES):
            return
        cleaned = self._cleaner.clean("", message)
        if cleaned is None:
            return
        label, style = _LEVEL_STYLES.get(level.upper(), _LEVEL_STYLES["INFO"])
        self._line(label, cleaned, **style)


def _prompt_text(user_prompt: Any) -> str:
    """The prompt text inside request_data's user_prompt JSON (which also carries the screenshot)."""
    if not isinstance(user_prompt, str):
        return ""
    try:
        parsed = json.loads(user_prompt)
    except json.JSONDecodeError:
        return user_prompt
    return parsed.get("text", "") if isinstance(parsed, dict) else user_prompt
