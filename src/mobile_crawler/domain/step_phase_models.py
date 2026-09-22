"""Domain models for step phase transitions."""

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class StepPhaseTransition:
    """A single phase transition record for a crawl step."""

    id: int | None
    run_id: int
    step_number: int
    from_phase: str  # "capture", "decide", etc.
    to_phase: str  # "capture", "decide", etc.
    timestamp: datetime  # ISO 8601 when transition occurred
    action_type: str | None = None  # which action triggered this
    duration_ms: float | None = None  # time spent in from_phase
    metadata_json: str | None = None  # optional extra context as JSON string
    current_package: str | None = None  # app package active during this transition
    current_activity: str | None = None  # activity component active during this transition


def build_timing_breakdown(transitions: Iterable[StepPhaseTransition]) -> dict[str, Any] | None:
    """Timing Breakdown of one step, from its phase transitions.

    Same rows as the GUI's Timing Breakdown: one "phase total" row per phase with a
    duration, plus one row per sub-phase metric (a11y_ms, omniparser_ms, manager_llm_ms,
    ...) from the transition metadata, and the Manager validation retries.

    Returns:
        Dict with total_step_duration_ms, phases, validation_retry_count and
        validation_retries, or None if the transitions carry no timing data.
    """
    phases: list[dict[str, Any]] = []
    validation_retries: list[dict[str, Any]] = []
    total_step_duration_ms = 0.0

    for transition in transitions:
        if transition.duration_ms is not None:
            duration_ms = float(transition.duration_ms)
            total_step_duration_ms += duration_ms
            phases.append({"phase": transition.from_phase, "metric": "phase total", "duration_ms": duration_ms})

        if not transition.metadata_json:
            continue
        try:
            metadata = json.loads(transition.metadata_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(metadata, dict):
            continue

        for metric, sub_duration_ms in (metadata.get("sub_phases") or {}).items():
            try:
                duration_ms = float(sub_duration_ms)
            except (TypeError, ValueError):
                continue
            phases.append({"phase": transition.from_phase, "metric": metric, "duration_ms": duration_ms})
        validation_retries.extend(metadata.get("validation_retries") or [])

    if not phases and not validation_retries:
        return None
    return {
        "total_step_duration_ms": total_step_duration_ms or None,
        "phases": phases,
        "validation_retry_count": len(validation_retries),
        "validation_retries": validation_retries,
    }
