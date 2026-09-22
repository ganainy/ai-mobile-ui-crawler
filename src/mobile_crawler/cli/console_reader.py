"""One reader of stdin shared by every CLI prompt in a crawl (Human Fallback, --step-by-step pauses).

Reading stdin has no native cross-platform timeout, so each read runs on a background thread and
lands on a queue the caller waits on. A caller that stops waiting (e.g. a Human Fallback prompt
timing out) can't cancel the blocked `input()` call, so the read stays pending. A later read reuses
that pending read instead of starting a second thread: two threads racing to read the same stdin
would risk delivering the user's answer to the wrong prompt, or corrupting it.
"""

import queue
import threading


class ConsoleReader:
    """Serializes stdin reads so at most one thread is ever reading."""

    def __init__(self, input_func=input):
        self._input_func = input_func
        self._lock = threading.Lock()
        self._pending_thread: threading.Thread | None = None
        self._pending_answers: queue.Queue[str] | None = None

    def read_async(self, prompt: str) -> "tuple[queue.Queue[str], bool]":
        """Start reading a line (EOF reads as "") and return the queue it will land on.

        The bool is True when an earlier, still-pending read was reused (its prompt was already
        shown, so `prompt` was not).
        """
        with self._lock:
            if self._pending_thread is not None and self._pending_thread.is_alive():
                assert self._pending_answers is not None
                return self._pending_answers, True

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
            return answers, False
