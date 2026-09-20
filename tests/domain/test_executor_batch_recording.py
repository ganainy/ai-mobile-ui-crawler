"""Recording an Action Batch: one history entry per action, one step."""

from mobile_crawler.domain.crawler_agent.agent.droid.state import CrawlerAgentState


def _batch_result():
    return {
        "action": {"action": "click", "index": 4},
        "outcome": False,
        "error": "click failed",
        "summary": "click failed",
        "results": [
            {"action": {"action": "type", "index": 5, "text": "x"}, "outcome": True, "error": "", "summary": "typed"},
            {
                "action": {"action": "click", "index": 4},
                "outcome": False,
                "error": "click failed",
                "summary": "click failed",
            },
        ],
    }


def test_batch_is_recorded_as_one_history_entry_per_action():
    state = CrawlerAgentState()

    state.record_executor_result(_batch_result())

    assert [a["action"] for a in state.action_history] == ["type", "click"]
    assert state.summary_history == ["typed", "click failed"]
    assert state.action_outcomes == [True, False]
    assert state.error_descriptions == ["", "click failed"]
    assert state.last_action == {"action": "click", "index": 4}
    assert state.last_summary == "click failed"


def test_single_action_result_without_results_is_recorded_once():
    state = CrawlerAgentState()

    state.record_executor_result(
        {"action": {"action": "click", "index": 1}, "outcome": True, "error": "", "summary": "ok"}
    )

    assert state.action_history == [{"action": "click", "index": 1}]
    assert state.action_outcomes == [True]


def test_recording_a_batch_does_not_advance_the_step_counter():
    state = CrawlerAgentState()
    before = state.step_number

    state.record_executor_result(_batch_result())

    assert state.step_number == before
