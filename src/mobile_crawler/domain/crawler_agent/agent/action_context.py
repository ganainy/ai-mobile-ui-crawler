"""ActionContext — composed bag of dependencies for action functions.

Replaces the ``tools=tools_instance`` parameter that action functions
previously received.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mobile_crawler.domain.crawler_agent.agent.droid.state import CrawlerAgentState
    from mobile_crawler.domain.crawler_agent.credential_manager import CredentialManager
    from mobile_crawler.domain.crawler_agent.tools.driver.base import DeviceDriver
    from mobile_crawler.domain.crawler_agent.tools.ui.provider import StateProvider
    from mobile_crawler.domain.crawler_agent.tools.ui.state import UIState


class ActionContext:
    """Everything an action function needs to interact with the device."""

    def __init__(
        self,
        driver: DeviceDriver,
        ui: UIState | None,
        shared_state: CrawlerAgentState,
        state_provider: StateProvider,
        app_opener_llm=None,
        credential_manager: CredentialManager | None = None,
        streaming: bool = False,
    ) -> None:
        self.driver = driver
        self.ui = ui  # refreshed each step before tool execution
        self.shared_state = shared_state
        self.state_provider = state_provider
        self.app_opener_llm = app_opener_llm
        self.credential_manager = credential_manager
        self.streaming = streaming
