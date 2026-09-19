"""Stop Reason and guided-progress derivation for a finished run."""

import json

from mobile_crawler.domain.run_outcome import build_guided_progress, derive_stop_reason


def test_user_cancel_wins_over_everything():
    assert (
        derive_stop_reason(
            cancel_requested=True,
            success=True,
            final_state={"stop_kind": "step_limit"},
            error_message=None,
        )
        == "user_stop"
    )


def test_agent_reported_limits_pass_through():
    for kind in ("step_limit", "duration_limit"):
        assert (
            derive_stop_reason(
                cancel_requested=False, success=True, final_state={"stop_kind": kind}, error_message=None
            )
            == kind
        )


def test_success_without_a_limit_is_agent_finished():
    assert (
        derive_stop_reason(cancel_requested=False, success=True, final_state={}, error_message=None) == "agent_finished"
    )


def test_failure_includes_the_error_message():
    assert (
        derive_stop_reason(cancel_requested=False, success=False, final_state={}, error_message="device offline")
        == "error: device offline"
    )


def test_failure_without_message_is_still_an_error():
    assert (
        derive_stop_reason(cancel_requested=False, success=False, final_state=None, error_message=None)
        == "error: unknown"
    )


def test_guided_progress_records_scenarios_and_what_the_agent_still_planned():
    raw = build_guided_progress(
        scenarios=["Open settings", "Log a meal"],
        final_plan="1. Log a meal",
        last_subgoal="Log a meal",
    )

    assert json.loads(raw) == {
        "scenarios": ["Open settings", "Log a meal"],
        "final_plan": "1. Log a meal",
        "last_subgoal": "Log a meal",
    }


def test_guided_progress_is_none_when_the_app_has_no_guided_scenarios():
    assert build_guided_progress(scenarios=[], final_plan="x", last_subgoal="y") is None
    assert build_guided_progress(scenarios=None, final_plan="x", last_subgoal="y") is None
