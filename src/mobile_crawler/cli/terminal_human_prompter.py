"""Terminal bridge for Human Fallback: blocks the calling (crawl) thread on a console prompt.

The stdin read goes through a `ConsoleReader` while this thread waits on its queue with the
timeout. On timeout, the read is abandoned rather than cancelled (Python can't interrupt a blocking
`input()` call) and the crawl auto-skips authentication, matching the GUI dialog's timeout behavior.

Authentication can call this prompter more than once per run (e.g. an email code lookup falling
back to an SMS code lookup), and `crawl --step-by-step` prompts on the same stdin; the shared
`ConsoleReader` makes a later prompt reuse an abandoned read instead of racing it.
"""

import queue

from mobile_crawler.cli.console_reader import ConsoleReader
from mobile_crawler.domain.human_fallback import HumanReply, HumanRequest, RequestKind


class TerminalHumanPrompter:
    """HumanPrompter implementation that prompts on the terminal."""

    def __init__(self, input_func=input, output_func=print, reader: ConsoleReader | None = None):
        self._output_func = output_func
        self._reader = reader or ConsoleReader(input_func=input_func)

    def __call__(self, request: HumanRequest, timeout_seconds: float) -> HumanReply | None:
        self._output_func(f"\n[Human Fallback] {request.message}")
        prompt = (
            "Enter verification code (blank or 'skip' to skip authentication): "
            if request.kind is RequestKind.CODE
            else "Press Enter when done (or type 'skip' to skip authentication): "
        )

        answers, reused = self._reader.read_async(prompt)
        if reused:
            self._output_func("[Human Fallback] Still waiting on a previous prompt's input; reusing it.")
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
