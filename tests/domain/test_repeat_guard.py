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
    assert repeated_actions_hint([{"action": "wait"}] * 5, []) == ""


def test_handles_missing_or_short_summaries_and_bad_entries():
    hint = repeated_actions_hint([ACCEPT, "oops", ACCEPT], ["only one"])
    assert "done 2x" in hint


def test_only_recent_window_counts():
    old = [ACCEPT] * 4
    recent = [{"action": "click", "index": i} for i in range(10)]
    assert repeated_actions_hint(old + recent, []) == ""
