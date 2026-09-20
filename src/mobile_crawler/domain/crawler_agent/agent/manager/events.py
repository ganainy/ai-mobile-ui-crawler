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

    # Real AI Monitor fields (populated at get_response; no behavior change)
    system_prompt: str | None = None
    user_prompt_text: str | None = None
    screenshot: bytes | None = None

    # Success/error signals for AI Monitor panel status indicators
    success: bool = True
    error: str | None = None

    # Whether vision was enabled for this call — when False, no screenshot was
    # ever captured/sent by design (a text-based UI description was used
    # instead), so the AI Monitor should say "not needed" rather than "missing"
    vision_enabled: bool = True

    # Indexed UI elements from the accessibility tree / OmniParser for this
    # step's screenshot — carried through so the overlay renderer can display
    # them in the Statistics panel and AI Monitor's Show Details view.
    elements: list[dict] | None = None

    # Whether a navigation loop (stuck) was detected on this step. Set by the
    # manager's state-graph tracker before the LLM call; consumed by the stats
    # collector to count stuck detections / recoveries.
    loop_detected: bool = False

    # OmniParser call duration for this step's state fetch, when OmniParser
    # actually ran (a11y fallback / omniparser-only mode); None otherwise.
    omniparser_ms: float | None = None

    # Portal a11y fetch duration for this step, and whether the a11y tree was
    # the element source (False when OmniParser replaced it).
    a11y_ms: float | None = None
    a11y_used: bool | None = None


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
