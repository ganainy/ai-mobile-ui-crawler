from typing import Any

from llama_index.core.workflow import Event


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
