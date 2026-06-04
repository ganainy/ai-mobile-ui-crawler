"""
Telemetry event models for Droidrun analytics.

This module defines Pydantic models for telemetry events captured during
agent execution. All events inherit from TelemetryEvent base class.
"""


from pydantic import BaseModel


class TelemetryEvent(BaseModel):
    """Base class for all telemetry events."""

    pass


class CrawlerAgentInitEvent(TelemetryEvent):
    """Event captured when CrawlerAgent is initialized."""

    goal: str
    llms: dict[str, str]
    tools: str
    max_steps: int
    timeout: int
    vision: dict[str, bool]
    reasoning: bool
    enable_tracing: bool
    debug: bool
    save_trajectories: str = "none"
    runtype: str = "developer"  # "cli" | "developer" | "web"
    custom_prompts: dict[str, str] | None = (
        None  # Keys: prompt names, Values: "custom" or None
    )


class PackageVisitEvent(TelemetryEvent):
    """Event captured when agent visits a new app package."""

    package_name: str
    activity_name: str
    step_number: int


class CrawlerAgentFinalizeEvent(TelemetryEvent):
    """Event captured when CrawlerAgent execution completes."""

    success: bool
    reason: str
    steps: int
    unique_packages_count: int
    unique_activities_count: int
