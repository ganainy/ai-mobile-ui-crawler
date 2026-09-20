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

    # Real AI Monitor fields (populated at get_response; no behavior change)
    prompt_text: str | None = None
    screenshot: bytes | None = None

    # Success/error signals for AI Monitor panel status indicators
    success: bool = True
    error: str | None = None

    # Whether vision was enabled for this call — when False, no screenshot was
    # ever captured/sent by design (a text-based UI description was used
    # instead), so the AI Monitor should say "not needed" rather than "missing"
    vision_enabled: bool = True

    # Already-parsed response (dict with 'thought'/'action'/'description') so
    # consumers like the AI Monitor and process_response don't re-parse the raw
    # text. None on the early-failure path (empty LLM response).
    parsed_action: dict | None = None

    # Indexed UI elements from the accessibility tree / OmniParser for this
    # step's screenshot — carried through so the overlay renderer can display
    # them in the Statistics panel and AI Monitor's Show Details view.
    elements: list[dict] | None = None


class ExecutorActionEvent(Event):
    """Action parsed, ready to execute."""

    action_json: str
    thought: str
    description: str
    full_response: str = ""
    actions: list[dict] = []  # ordered Action Batch; empty means use action_json


class ExecutorActionResultEvent(Event):
    """Action execution result (internal event with full details)."""

    action: dict
    success: bool
    error: str
    summary: str
    thought: str = ""
    full_response: str = ""
    results: list[dict] = []  # per-action outcomes of an Action Batch
