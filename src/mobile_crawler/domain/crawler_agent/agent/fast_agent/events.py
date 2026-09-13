"""
Events for the FastAgent workflow.

Internal events for streaming to frontend/logging.
"""


from llama_index.core.workflow import Event

from mobile_crawler.domain.crawler_agent.agent.usage import UsageResult


class FastAgentInputEvent(Event):
    """Input ready for LLM."""

    pass


class FastAgentResponseEvent(Event):
    """LLM response received."""

    thought: str
    code: str | None = None
    usage: UsageResult | None = None

    # Real AI Monitor fields (populated at handle_llm_input; no behavior change)
    raw_response: str | None = None
    prompt_text: str | None = None
    screenshot: bytes | None = None
    fast_agent_llm_ms: float | None = None

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

    # OmniParser call duration for this step's state fetch, when OmniParser
    # actually ran (a11y fallback / omniparser-only mode); None otherwise.
    omniparser_ms: float | None = None


class FastAgentToolCallEvent(Event):
    """Tool calls ready to execute."""

    tool_calls_repr: str


class FastAgentOutputEvent(Event):
    """Tool execution result."""

    output: str


class FastAgentEndEvent(Event):
    """FastAgent finished."""

    success: bool
    reason: str
    tool_call_count: int = 0
