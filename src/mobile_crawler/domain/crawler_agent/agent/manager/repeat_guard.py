"""Tell the manager exactly which recent actions it keeps repeating.

A generic "try something different" warning did not stop real runs from tapping the same button over and over
(e.g. ACCEPT on an age gate, 'close ad' loops). This lists the repeated actions so the prompt can forbid them.
"""

from __future__ import annotations

import json
from collections import Counter

REPEAT_WINDOW = 10
MIN_REPEATS = 2
MAX_LISTED = 4


def _key(action: object) -> str:
    try:
        return json.dumps(action, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return str(action)


def repeated_actions_hint(action_history: list, summary_history: list | None = None) -> str:
    """Return a 'do NOT repeat these' paragraph, or '' when nothing was repeated."""
    recent = list(action_history or [])[-REPEAT_WINDOW:]
    if len(recent) < MIN_REPEATS:
        return ""
    summaries = list(summary_history or [])[-REPEAT_WINDOW:]
    summaries = [""] * (len(recent) - len(summaries)) + summaries
    counts: Counter[str] = Counter()
    label: dict[str, str] = {}
    for action, summary in zip(recent, summaries):
        if not isinstance(action, dict) or action.get("action") in (None, "wait", "invalid"):
            continue
        k = _key(action)
        counts[k] += 1
        label[k] = (str(summary).strip() or k)[:100]
    repeated = [(k, n) for k, n in counts.most_common() if n >= MIN_REPEATS][:MAX_LISTED]
    if not repeated:
        return ""
    lines = [f"- {label[k]} (done {n}x in the last {len(recent)} steps)" for k, n in repeated]
    return (
        "You already did these actions several times and they did not make progress. Do NOT choose them again; "
        "pick a different element or a different kind of action (scroll, back, another button):\n" + "\n".join(lines)
    )
