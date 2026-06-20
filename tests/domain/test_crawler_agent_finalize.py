from unittest.mock import Mock

from mobile_crawler.domain.crawler_agent.agent.droid.crawler_agent import CrawlerAgent


def _agent_for_finalize(save_trajectory: str = "none") -> CrawlerAgent:
    agent = CrawlerAgent.__new__(CrawlerAgent)
    agent.config = Mock()
    agent.config.logging.save_trajectory = save_trajectory
    return agent


def test_max_step_finalization_skips_final_parsed_ui_state_without_trajectory():
    agent = _agent_for_finalize(save_trajectory="none")

    assert agent._final_ui_state_required("Reached maximum steps (5)") is False


def test_non_max_step_finalization_keeps_final_parsed_ui_state():
    agent = _agent_for_finalize(save_trajectory="none")

    assert agent._final_ui_state_required("Task completed") is True


def test_finalization_skips_final_parsed_ui_state_when_final_capture_disabled():
    agent = _agent_for_finalize(save_trajectory="none")

    assert agent._final_ui_state_required("Task completed", final_capture_enabled=False) is False


def test_trajectory_finalization_keeps_final_parsed_ui_state_at_max_steps():
    agent = _agent_for_finalize(save_trajectory="all")

    assert agent._final_ui_state_required("Reached maximum steps (5)") is True
