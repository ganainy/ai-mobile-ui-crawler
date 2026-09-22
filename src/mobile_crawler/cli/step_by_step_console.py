"""Terminal side of `crawl --step-by-step`: summarize each paused step, advance on Enter.

The agent pauses after a step has run (see `CrawlerLoop.set_step_by_step_enabled`), so the
summary is what that step did: one line per executed action. The CLI has no screenshot board or
live feed, so this is the user's only view of the step before choosing to continue.

This is an event listener (duck-typed: `CrawlerLoop` looks handlers up by name) for
`on_step_paused`, which is called on the agent's event-loop thread; waiting for Enter there would
stall the workflow, so the wait runs on a background thread that then calls `advance`.

Everything is written to stderr: stdout carries the crawl's newline-delimited JSON events.
"""

import threading
from collections.abc import Callable

import click

from mobile_crawler.cli.console_reader import ConsoleReader
from mobile_crawler.domain.models import ActionResult


def _echo_err(message: str) -> None:
    click.echo(message, err=True)


class StepByStepConsole:
    """Prints a paused step's summary and advances the crawl when the user presses Enter."""

    def __init__(
        self,
        advance: Callable[[], None],
        reader: ConsoleReader,
        output_func: Callable[[str], None] = _echo_err,
    ):
        self._advance = advance
        self._reader = reader
        self._output_func = output_func

    def on_step_paused(self, run_id: int, step_number: int, actions: list[ActionResult]) -> None:
        for line in _summary_lines(step_number, actions):
            self._output_func(line)
        self._output_func("[Step-by-step] Press Enter to run the next step (Ctrl+C to stop).")

        answers, _ = self._reader.read_async("")

        def _wait_then_advance() -> None:
            answers.get()
            self._advance()

        threading.Thread(target=_wait_then_advance, daemon=True).start()


def _summary_lines(step_number: int, actions: list[ActionResult]) -> list[str]:
    if not actions:
        return [f"\n[Step-by-step] Step {step_number} finished (no actions)."]
    count = f"{len(actions)} action{'s' if len(actions) != 1 else ''}"
    lines = [f"\n[Step-by-step] Step {step_number} finished ({count}):"]
    for i, action in enumerate(actions, start=1):
        status = "ok  " if action.success else "FAIL"
        lines.append(f"  {i}. {status} {action.action_type} ({action.duration_ms:.0f}ms): {action.target}")
    return lines
