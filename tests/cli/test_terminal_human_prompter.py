"""Tests for TerminalHumanPrompter (see mobile_crawler.domain.human_fallback.HumanPrompter)."""

import threading
import time

from mobile_crawler.cli.terminal_human_prompter import TerminalHumanPrompter
from mobile_crawler.domain.human_fallback import HumanReply, HumanRequest, RequestKind


def test_code_answered_returns_reply_with_code():
    prompter = TerminalHumanPrompter(input_func=lambda prompt: "424242", output_func=lambda msg: None)
    reply = prompter(HumanRequest(RequestKind.CODE, "code?"), timeout_seconds=5)
    assert reply == HumanReply(code="424242")


def test_manual_step_enter_continues():
    prompter = TerminalHumanPrompter(input_func=lambda prompt: "", output_func=lambda msg: None)
    reply = prompter(HumanRequest(RequestKind.MANUAL_STEP, "finish sign-in"), timeout_seconds=5)
    assert reply == HumanReply(code=None)


def test_typing_skip_declines():
    prompter = TerminalHumanPrompter(input_func=lambda prompt: "skip", output_func=lambda msg: None)
    reply = prompter(HumanRequest(RequestKind.CODE, "code?"), timeout_seconds=5)
    assert reply == HumanReply(skipped=True)


def test_blank_code_declines():
    prompter = TerminalHumanPrompter(input_func=lambda prompt: "   ", output_func=lambda msg: None)
    reply = prompter(HumanRequest(RequestKind.CODE, "code?"), timeout_seconds=5)
    assert reply == HumanReply(skipped=True)


def test_timeout_returns_none():
    never_answers = threading.Event()
    prompter = TerminalHumanPrompter(
        input_func=lambda prompt: never_answers.wait(), output_func=lambda msg: None
    )
    reply = prompter(HumanRequest(RequestKind.CODE, "code?"), timeout_seconds=0.05)
    assert reply is None


def test_messages_are_written_to_output():
    seen = []
    prompter = TerminalHumanPrompter(input_func=lambda prompt: "123", output_func=seen.append)
    prompter(HumanRequest(RequestKind.CODE, "Enter the SMS code"), timeout_seconds=5)
    assert any("Enter the SMS code" in msg for msg in seen)


def test_second_call_after_a_timeout_reuses_the_pending_reader_instead_of_racing_stdin():
    """A timed-out call leaves its reader thread blocked on stdin forever (input() can't be
    cancelled). A later call (e.g. email code lookup falling back to SMS) must not start a
    second thread also reading stdin -- that would race for the user's answer."""
    call_count = 0
    released = threading.Event()

    def input_func(prompt):
        nonlocal call_count
        call_count += 1
        released.wait(5)
        return "999999"

    prompter = TerminalHumanPrompter(input_func=input_func, output_func=lambda msg: None)

    first_reply = prompter(HumanRequest(RequestKind.CODE, "first"), timeout_seconds=0.05)
    assert first_reply is None

    result: dict = {}
    second_call = threading.Thread(
        target=lambda: result.setdefault(
            "reply", prompter(HumanRequest(RequestKind.CODE, "second"), timeout_seconds=5)
        )
    )
    second_call.start()
    time.sleep(0.2)  # let the second call reach _reader_queue()
    assert call_count == 1  # no second thread was started to read stdin

    released.set()
    second_call.join(3)
    assert result["reply"] == HumanReply(code="999999")
