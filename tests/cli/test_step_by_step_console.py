"""Tests for StepByStepConsole: the CLI's pause summary + press-Enter-to-advance for --step-by-step."""

import threading

from mobile_crawler.cli.console_reader import ConsoleReader
from mobile_crawler.cli.step_by_step_console import StepByStepConsole
from mobile_crawler.domain.models import ActionResult


def _console(input_func, advance, seen=None):
    return StepByStepConsole(
        advance=advance,
        reader=ConsoleReader(input_func=input_func),
        output_func=(seen.append if seen is not None else (lambda msg: None)),
    )


def test_enter_advances_the_crawl():
    advanced = threading.Event()
    console = _console(lambda prompt: "", advanced.set)

    console.on_step_paused(42, 1, [])

    assert advanced.wait(2)


def test_pause_does_not_block_the_caller_while_waiting_for_enter():
    """on_step_paused runs on the agent's event-loop thread; blocking it would stall the workflow."""
    release = threading.Event()
    advanced = threading.Event()
    console = _console(lambda prompt: release.wait(5) and "", advanced.set)

    console.on_step_paused(42, 1, [])  # returns while input is still pending

    assert not advanced.is_set()
    release.set()
    assert advanced.wait(2)


def test_summary_lists_each_action_of_the_paused_step():
    seen = []
    console = _console(lambda prompt: "", lambda: None, seen)

    console.on_step_paused(
        42,
        3,
        [
            ActionResult(success=True, action_type="click", target="Tapped 'Login'", duration_ms=120.4),
            ActionResult(success=False, action_type="type", target="No focused field", duration_ms=5),
        ],
    )

    text = "\n".join(seen)
    assert "Step 3" in text
    assert "2 actions" in text
    assert "click" in text and "Tapped 'Login'" in text and "120ms" in text
    assert "type" in text and "No focused field" in text
    assert "FAIL" in text
    assert "Enter" in text


def test_summary_says_when_the_step_ran_no_actions():
    seen = []
    console = _console(lambda prompt: "", lambda: None, seen)

    console.on_step_paused(42, 1, [])

    assert any("no actions" in msg for msg in seen)


def test_eof_on_stdin_still_advances_so_the_crawl_cannot_hang():
    advanced = threading.Event()

    def eof(prompt):
        raise EOFError

    console = _console(eof, advanced.set)
    console.on_step_paused(42, 1, [])

    assert advanced.wait(2)
