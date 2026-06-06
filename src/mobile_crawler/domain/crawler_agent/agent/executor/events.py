"""
Events for the ExecutorAgent workflow.

Internal events for streaming to frontend/logging.
For CrawlerAgent coordination events, see droid/events.py
"""


from llama_index.core.workflow import Event

from mobile_crawler.domain.crawler_agent.agent.usage import UsageResult


class ExecutorContextEvent(Event):
    """Context prepared, ready for LLM call."""

    subgoal: str


class ExecutorResponseEvent(Event):
    """LLM response received, ready for parsing."""

    response: str
    usage: UsageResult | None = None
    executor_llm_ms: float | None = None


class ExecutorActionEvent(Event):
    """Action parsed, ready to execute."""

    action_json: str
    thought: str
    description: str
    full_response: str = ""


class ExecutorActionResultEvent(Event):
    """Action execution result (internal event with full details)."""

    action: dict
    success: bool
    error: str
    summary: str
    thought: str = ""
    full_response: str = ""
