"""Domain models for step phase transitions."""

from dataclasses import dataclass
from datetime import datetime


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
