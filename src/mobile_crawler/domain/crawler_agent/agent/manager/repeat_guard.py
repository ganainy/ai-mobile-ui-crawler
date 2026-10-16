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
WAIT_WINDOW = 6
MIN_WAITS = 2


def _key(action: object) -> str:
    try:
        return json.dumps(action, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return str(action)


def _is_zero_length_swipe(action: dict) -> bool:
    return action.get("action") == "swipe" and action.get("coordinate") is not None and (
        action.get("coordinate") == action.get("coordinate2")
    )


def _kind(action: dict) -> str | None:
    """Coarse action kind used to suggest what has NOT been tried lately."""
    name = action.get("action")
    if name == "system_button":
        return f"press {action.get('button', 'a system button')}"
    if name == "swipe":
        return None if _is_zero_length_swipe(action) else "swipe"
    if name in ("click", "click_at", "click_area"):
        return "tap"
    if name in ("long_press", "long_press_at"):
        return "long press"
    return name if name in ("open_app", "type") else None


_STRUCTURAL_OPTIONS = (
    ("press back", "press the Back button"),
    ("swipe", "swipe across the screen (a real swipe from one point to a different point)"),
    ("open_app", "relaunch the app with open_app"),
    ("long press", "long-press something"),
)


def repeated_actions_hint(action_history: list, summary_history: list | None = None) -> str:
    """Return a 'do NOT repeat these' paragraph, or '' when the recent actions were not repetitive.

    Covers three stalls seen in real runs: the same element tapped again and again (ACCEPT on an age gate, 'close ad'),
    repeated waiting on a screen that does not change (Cut the Rope), and zero-length swipes that do nothing.
    """
    history = [a for a in (action_history or []) if isinstance(a, dict)]
    recent = history[-REPEAT_WINDOW:]
    if len(recent) < MIN_REPEATS:
        return ""
    summaries = list(summary_history or [])[-len(action_history or []):] if action_history else []
    summaries = [""] * (len(action_history or []) - len(summaries)) + summaries
    # align summaries with the filtered history
    paired = [(a, summaries[i]) for i, a in enumerate(action_history or []) if isinstance(a, dict)][-REPEAT_WINDOW:]

    counts: Counter[str] = Counter()
    label: dict[str, str] = {}
    for action, summary in paired:
        if action.get("action") in (None, "wait", "invalid"):
            continue
        k = _key(action)
        counts[k] += 1
        label[k] = (str(summary).strip() or k)[:100]
    repeated = [(k, n) for k, n in counts.most_common() if n >= MIN_REPEATS][:MAX_LISTED]

    recent_short = history[-WAIT_WINDOW:]
    waits = sum(1 for a in recent_short if a.get("action") == "wait")
    zero_swipes = sum(1 for a in recent[-WAIT_WINDOW:] if _is_zero_length_swipe(a))

    if not repeated and waits < MIN_WAITS and not zero_swipes:
        return ""

    lines: list[str] = []
    if repeated:
        lines.append(
            "You already did these actions several times and they did not make progress. Do NOT choose them again:\n"
            + "\n".join(f"- {label[k]} (done {n}x in the last {len(recent)} steps)" for k, n in repeated)
        )
    if waits >= MIN_WAITS:
        lines.append(
            f"You waited {waits} times in the last {len(recent_short)} steps and the screen did not change. "
            "Waiting does not help: do NOT wait again."
        )
    if zero_swipes:
        lines.append(
            "A swipe whose start and end point are the same does nothing. If you swipe, use two different points."
        )
    used = {k for a in recent if (k := _kind(a))}
    untried = [text for key, text in _STRUCTURAL_OPTIONS if key not in used]
    if untried:
        lines.append("Do something structurally different, for example: " + "; ".join(untried[:3]) + ".")
    else:
        lines.append("Do something structurally different from the last steps (another element, area or action type).")
    return "\n".join(lines)
