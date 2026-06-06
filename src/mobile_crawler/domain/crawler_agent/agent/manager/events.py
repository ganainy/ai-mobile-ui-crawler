"""
Events for the ManagerAgent workflow.

Internal events for streaming to frontend/logging.
For CrawlerAgent coordination events, see droid/events.py
"""


from llama_index.core.workflow import Event

from mobile_crawler.domain.crawler_agent.agent.usage import UsageResult


class ManagerContextEvent(Event):
    """Context prepared, ready for LLM call."""

    app_card_load_ms: float | None = None


class ManagerResponseEvent(Event):
    """LLM response received, ready for parsing."""

    response: str
    usage: UsageResult | None = None
    manager_llm_ms: float | None = None
    validation_retries: list[dict] | None = None


class ManagerPlanDetailsEvent(Event):
    """Plan parsed and ready (internal event with full details)."""

    plan: str
    subgoal: str
    thought: str
    answer: str = ""
    memory_update: str = ""
    progress_summary: str = ""
    success: bool | None = None  # True/False if complete, None if in progress
    full_response: str = ""
