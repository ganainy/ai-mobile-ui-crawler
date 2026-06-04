"""
CrawlerAgent coordination events.

These events route between CrawlerAgent and child agents.
For internal agent events, see each agent's events.py file.
"""


from llama_index.core.workflow import Event, StopEvent
from pydantic import BaseModel


class FastAgentExecuteEvent(Event):
    instruction: str


class FastAgentResultEvent(Event):
    success: bool
    reason: str
    instruction: str


# ============================================================================
# Manager/Executor coordination events
# ============================================================================


class ManagerInputEvent(Event):
    """Trigger Manager workflow for planning"""

    pass


class ManagerPlanEvent(Event):
    """
    Coordination event from ManagerAgent to CrawlerAgent.

    Used for workflow step routing only (NOT streamed to frontend).
    For internal events with memory_update metadata, see ManagerPlanDetailsEvent.
    """

    plan: str
    current_subgoal: str
    thought: str
    answer: str = ""
    success: bool | None = None  # True/False if complete, None if in progress


class ExecutorInputEvent(Event):
    """Trigger Executor workflow for action execution"""

    current_subgoal: str


class ExecutorResultEvent(Event):
    """Executor finished with action result."""

    action: dict
    outcome: bool
    error: str
    summary: str


# ============================================================================
# EXTERNAL USER MESSAGE EVENTS
# ============================================================================


class ExternalUserMessageAppliedEvent(Event):
    message_ids: list[str]
    consumer: str
    step_number: int


class ExternalUserMessageDroppedEvent(Event):
    message_ids: list[str]
    reason: str
    step_number: int


# ============================================================================
# FINALIZATION EVENTS
# ============================================================================


class FinalizeEvent(Event):
    """Trigger finalization."""

    success: bool
    reason: str


class ResultEvent(StopEvent):
    """
    Final result from CrawlerAgent.

    Returned by CrawlerAgent.run() with:
    - success: Whether the task completed successfully
    - reason: Explanation or answer
    - steps: Number of steps taken
    - structured_output: Extracted structured data (if output_model was provided)
    """

    success: bool
    reason: str
    steps: int
    structured_output: BaseModel | None = None
