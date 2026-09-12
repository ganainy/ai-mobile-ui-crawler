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
