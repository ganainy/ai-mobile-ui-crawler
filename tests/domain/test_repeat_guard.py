from mobile_crawler.domain.crawler_agent.agent.manager.repeat_guard import repeated_actions_hint

ACCEPT = {"action": "click", "index": 7}
CHECK = {"action": "click", "index": 3}


def test_lists_repeated_actions_with_summaries():
    hist = [CHECK, ACCEPT, ACCEPT, ACCEPT, {"action": "wait"}]
    summ = ["Ticked the terms box", "Tapped ACCEPT", "Tapped ACCEPT", "Tapped ACCEPT", "Waited"]
    hint = repeated_actions_hint(hist, summ)
    assert "Tapped ACCEPT (done 3x" in hint
    assert "Ticked the terms box" not in hint and "Waited" not in hint


def test_empty_when_nothing_repeats():
    assert repeated_actions_hint([CHECK, ACCEPT], ["a", "b"]) == ""
    assert repeated_actions_hint([], []) == ""
    assert "do NOT wait again" in repeated_actions_hint([{"action": "wait"}] * 5, [])


def test_handles_missing_or_short_summaries_and_bad_entries():
    hint = repeated_actions_hint([ACCEPT, "oops", ACCEPT], ["only one"])
    assert "done 2x" in hint


def test_only_recent_window_counts():
    old = [ACCEPT] * 4
    recent = [{"action": "click", "index": i} for i in range(10)]
    assert repeated_actions_hint(old + recent, []) == ""


WAIT = {"action": "wait", "duration": 2.0}
BACK = {"action": "system_button", "button": "back"}


def test_repeated_waiting_is_called_out_and_back_is_suggested():
    hint = repeated_actions_hint([CHECK, WAIT, WAIT, WAIT], ["a", "w", "w", "w"])
    assert "waited 3 times" in hint and "do NOT wait again" in hint
    assert "press the Back button" in hint


def test_zero_length_swipe_is_flagged():
    stuck = {"action": "swipe", "coordinate": [540, 300], "coordinate2": [540, 300], "duration": 1}
    hint = repeated_actions_hint([CHECK, stuck], ["a", "b"])
    assert "same does nothing" in hint


def test_a_single_wait_is_not_a_stall():
    assert repeated_actions_hint([CHECK, ACCEPT, WAIT], ["a", "b", "c"]) == ""


def test_untried_options_exclude_what_was_used():
    hint = repeated_actions_hint([ACCEPT, ACCEPT, BACK], ["x", "x", "b"])
    assert "press the Back button" not in hint and "swipe" in hint
