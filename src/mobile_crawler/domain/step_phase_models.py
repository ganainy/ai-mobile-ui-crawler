"""Domain models for step phase transitions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class StepPhaseTransition:
    """A single phase transition record for a crawl step."""

    id: Optional[int]
    run_id: int
    step_number: int
    from_phase: str  # "capture", "decide", etc.
    to_phase: str  # "capture", "decide", etc.
    timestamp: datetime  # ISO 8601 when transition occurred
    action_type: Optional[str] = None  # which action triggered this
    duration_ms: Optional[float] = None  # time spent in from_phase
    metadata_json: Optional[str] = None  # optional extra context as JSON string
