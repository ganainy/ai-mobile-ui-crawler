"""Detect Manager subgoals that are only a status note ("... (done)") and carry no action."""

from __future__ import annotations

import re

_WORD = r"(?:done|completed?|finished)"
_FINISHED = re.compile(
    rf"(\(\s*{_WORD}\s*\)\s*\.?\s*$)"  # "... (done)"
    rf"|(^\s*[\[(]\s*{_WORD}\s*[\])])"  # "[Done] ..." / "(done) ..."
    rf"|(^\s*{_WORD}\s*[:\-\u2013]\s)"  # "Done: ..." / "Done - ..."
    rf"|(^\s*{_WORD}\s*[.!]?\s*$)",  # bare "done"
    re.IGNORECASE,
)

NEXT_ACTION_SUBGOAL = (
    "The previous subgoal is already finished. Do NOT wait. Interact with the next unexplored, visible "
    "interactive element on the current screen (one you have not used yet). If nothing new is left, "
    "scroll or press Back to reach a screen you have not seen."
)


def is_finished_subgoal(subgoal: str | None) -> bool:
    """True when the subgoal only reports that a goal is done (so the Executor would just wait)."""
    return bool(subgoal) and bool(_FINISHED.search(subgoal.strip()))
