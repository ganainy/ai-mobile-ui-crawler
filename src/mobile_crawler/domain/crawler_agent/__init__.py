"""
Droidrun - A framework for controlling Android devices through LLM agents.
"""

import logging

from mobile_crawler.domain.crawler_agent.agent import ResultEvent
from mobile_crawler.domain.crawler_agent.agent.droid import CrawlerAgent
from mobile_crawler.domain.crawler_agent.agent.utils.llm_picker import load_llm
from mobile_crawler.domain.crawler_agent.config_manager import (
    AgentConfig,
    AppCardConfig,
    CredentialsConfig,
    DeviceConfig,
    DroidConfig,
    ExecutorConfig,
    FastAgentConfig,
    LLMProfile,
    LoggingConfig,
    ManagerConfig,
    TelemetryConfig,
    ToolsConfig,
    TracingConfig,
)
from mobile_crawler.domain.crawler_agent.log_handlers import CLILogHandler
from mobile_crawler.domain.crawler_agent.macro import MacroPlayer, replay_macro_file, replay_macro_folder
from mobile_crawler.domain.crawler_agent.tools import AndroidDriver, DeviceDriver, RecordingDriver

__version__ = "0.1.0"

# Attach a default CLILogHandler so that every consumer (CLI, TUI, SDK,
# tools-only) gets visible output without explicit setup. CLI and TUI
# replace this with their own handler via ``configure_logging()``.
_logger = logging.getLogger("crawler_agent")
_logger.addHandler(CLILogHandler())
_logger.setLevel(logging.INFO)
_logger.propagate = False

__all__ = [
    # Agent
    "CrawlerAgent",
    "load_llm",
    "ResultEvent",
    # Tools / Drivers
    "DeviceDriver",
    "AndroidDriver",
    "RecordingDriver",
    # Macro
    "MacroPlayer",
    "replay_macro_file",
    "replay_macro_folder",
    # Configuration
    "DroidConfig",
    "AgentConfig",
    "FastAgentConfig",
    "ManagerConfig",
    "ExecutorConfig",
    "AppCardConfig",
    "DeviceConfig",
    "LoggingConfig",
    "TracingConfig",
    "TelemetryConfig",
    "ToolsConfig",
    "CredentialsConfig",
    "LLMProfile",
]
