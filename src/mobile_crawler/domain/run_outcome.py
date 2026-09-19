"""Derives the Stop Reason and guided-scenario progress recorded on a finished run."""

import json
from typing import Any


def derive_stop_reason(
    cancel_requested: bool,
    success: bool,
    final_state: dict[str, Any] | None,
    error_message: str | None,
) -> str:
    """Return why a run ended: user_stop, step_limit, duration_limit, agent_finished or error: <msg>."""
    if cancel_requested:
        return "user_stop"
    if not success:
        return f"error: {error_message or 'unknown'}"
    return (final_state or {}).get("stop_kind") or "agent_finished"


def build_guided_progress(
    scenarios: list[str] | None,
    final_plan: str | None,
    last_subgoal: str | None,
) -> str | None:
    """Serialise what is known about guided-scenario progress, or None if the app has none.

    The agent has no structured "scenario done" signal, so this records the scenarios that were
    configured plus the agent's last plan and subgoal, which show what it still considered open.
    """
    if not scenarios:
        return None
    return json.dumps(
        {
            "scenarios": list(scenarios),
            "final_plan": final_plan,
            "last_subgoal": last_subgoal,
        }
    )
