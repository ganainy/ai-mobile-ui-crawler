from mobile_crawler.domain.crawler_agent.agent.manager.subgoal_guard import NEXT_ACTION_SUBGOAL, is_finished_subgoal


def test_done_status_notes_are_finished():
    assert is_finished_subgoal("Startup consent and terms handled, at main menu. (done)")
    assert is_finished_subgoal("Consent dialog dismissed (Done).")
    assert is_finished_subgoal("done")
    assert is_finished_subgoal("Completed.")


def test_real_subgoals_are_not_finished():
    assert not is_finished_subgoal("Tap the Play button on the main menu")
    assert not is_finished_subgoal("Wait until the done button appears, then tap it")
    assert not is_finished_subgoal("")
    assert not is_finished_subgoal(None)


def test_replacement_subgoal_is_actionable():
    assert "Do NOT wait" in NEXT_ACTION_SUBGOAL
