from typing import Any

from llama_index.core.workflow import Event, StopEvent
from pydantic import BaseModel


class FastAgentExecuteEvent(Event):
    instruction: str


class FastAgentResultEvent(Event):
    success: bool
    reason: str
    instruction: str


class ManagerInputEvent(Event):
    """Trigger Manager workflow for planning."""

    pass


class ManagerPlanEvent(Event):
    """Coordination event from ManagerAgent to CrawlerAgent."""

    plan: str
    current_subgoal: str
    thought: str
    answer: str = ""
    success: bool | None = None


class ExecutorInputEvent(Event):
    """Trigger Executor workflow for action execution."""

    current_subgoal: str


class ExecutorResultEvent(Event):
    """Executor finished with action result."""

    action: dict
    outcome: bool
    error: str
    summary: str


class ExternalUserMessageAppliedEvent(Event):
    message_ids: list[str]
    consumer: str
    step_number: int


class ExternalUserMessageDroppedEvent(Event):
    message_ids: list[str]
    reason: str
    step_number: int


class FinalizeEvent(Event):
    """Trigger finalization."""

    success: bool
    reason: str


class ResultEvent(StopEvent):
    """Final result from CrawlerAgent."""

    success: bool
    reason: str
    steps: int
    structured_output: BaseModel | None = None


class ScreenshotEvent(Event):
    screenshot: bytes


class RecordUIStateEvent(Event):
    ui_state: list[dict[str, Any]]


class ToolExecutionEvent(Event):
    """Emitted after every tool call dispatched through ToolRegistry."""

    tool_name: str
    tool_args: dict[str, Any]
    success: bool
    summary: str
    duration_ms: float | None = None
