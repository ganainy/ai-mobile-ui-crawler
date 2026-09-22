"""Terminal bridge for Human Fallback: blocks the calling (crawl) thread on a console prompt.

Reading stdin has no native cross-platform timeout, so the read runs on a background thread while
this thread waits on a queue with the timeout. On timeout, the read is abandoned rather than
cancelled (Python can't interrupt a blocking `input()` call) and the crawl auto-skips
authentication, matching the GUI dialog's timeout behavior.

Authentication can call this prompter more than once per run (e.g. an email code lookup falling
back to an SMS code lookup). An abandoned read from a timed-out call stays blocked on stdin, so a
later call reuses that same pending read instead of starting a second one — two threads racing to
read the same stdin would risk delivering the user's answer to the wrong call, or corrupting it.
"""

import queue
import threading

from mobile_crawler.domain.human_fallback import HumanReply, HumanRequest, RequestKind


class TerminalHumanPrompter:
    """HumanPrompter implementation that prompts on the terminal."""

    def __init__(self, input_func=input, output_func=print):
        self._input_func = input_func
        self._output_func = output_func
        self._lock = threading.Lock()
        self._pending_thread: threading.Thread | None = None
        self._pending_answers: queue.Queue[str] | None = None

    def __call__(self, request: HumanRequest, timeout_seconds: float) -> HumanReply | None:
        self._output_func(f"\n[Human Fallback] {request.message}")
        prompt = (
            "Enter verification code (blank or 'skip' to skip authentication): "
            if request.kind is RequestKind.CODE
            else "Press Enter when done (or type 'skip' to skip authentication): "
        )

        answers = self._reader_queue(prompt)
        try:
            answer = (answers.get(timeout=timeout_seconds) or "").strip()
        except queue.Empty:
            self._output_func("[Human Fallback] Timed out waiting for input; skipping authentication.")
            return None

        if answer.lower() == "skip":
            return HumanReply(skipped=True)
        if request.kind is RequestKind.CODE:
            return HumanReply(code=answer) if answer else HumanReply(skipped=True)
        return HumanReply(code=None)

    def _reader_queue(self, prompt: str) -> "queue.Queue[str]":
        """The queue a stdin read will land on: a fresh reader, or one already pending from a
        previous call's timeout (reused so only one thread ever reads stdin at a time)."""
        with self._lock:
            if self._pending_thread is not None and self._pending_thread.is_alive():
                self._output_func("[Human Fallback] Still waiting on a previous prompt's input; reusing it.")
                assert self._pending_answers is not None
                return self._pending_answers

            answers: queue.Queue[str] = queue.Queue(maxsize=1)

            def _read() -> None:
                try:
                    answers.put(self._input_func(prompt))
                except EOFError:
                    answers.put("")

            thread = threading.Thread(target=_read, daemon=True)
            self._pending_thread = thread
            self._pending_answers = answers
            thread.start()
            return answers
