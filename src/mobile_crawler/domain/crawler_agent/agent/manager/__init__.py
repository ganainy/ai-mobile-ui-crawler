"""
Manager Agent - Planning and reasoning workflow.

Two variants available:
- ManagerAgent: Stateful, maintains chat history
- StatelessManagerAgent: Stateless, rebuilds context each turn
"""

from mobile_crawler.domain.crawler_agent.agent.common.events import ManagerInputEvent, ManagerPlanEvent
from mobile_crawler.domain.crawler_agent.agent.manager.events import (
    ManagerContextEvent,
    ManagerPlanDetailsEvent,
    ManagerResponseEvent,
)
from mobile_crawler.domain.crawler_agent.agent.manager.manager_agent import ManagerAgent
from mobile_crawler.domain.crawler_agent.agent.manager.prompts import parse_manager_response
from mobile_crawler.domain.crawler_agent.agent.manager.stateless_manager_agent import StatelessManagerAgent

__all__ = [
    "ManagerAgent",
    "StatelessManagerAgent",
    "ManagerInputEvent",
    "ManagerPlanEvent",
    "ManagerContextEvent",
    "ManagerResponseEvent",
    "ManagerPlanDetailsEvent",
    "parse_manager_response",
]
