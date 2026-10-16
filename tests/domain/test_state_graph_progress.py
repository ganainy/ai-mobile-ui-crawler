from mobile_crawler.domain.state_graph import StateGraphTracker


def els(*texts, shift=0):
    return [{"text": t, "bounds": f"[{shift + i},{i}][{shift + i + 10},{i + 10}]", "className": "x"} for i, t in enumerate(texts)]


def test_layout_hash_changes_with_bounds_but_content_hash_does_not():
    t = StateGraphTracker(run_id=0)
    a, b = els("PLAY", "SETTINGS", shift=0), els("PLAY", "SETTINGS", shift=7)
    assert t.compute_layout_hash(a) != t.compute_layout_hash(b)
    assert t.compute_content_hash(a) == t.compute_content_hash(b)


def test_no_progress_after_six_steps_without_new_content():
    t = StateGraphTracker(run_id=0)
    assert t.record_content(els("PLAY")) is True
    for i in range(5):
        assert t.record_content(els("PLAY", shift=i + 1)) is False  # animated, same labels
    assert t.detect_no_progress(6) is False  # the first (new) step is still inside the window
    t.record_content(els("PLAY", shift=9))
    assert t.detect_no_progress(6) is True


def test_new_content_resets_no_progress():
    t = StateGraphTracker(run_id=0)
    for i in range(8):
        t.record_content(els("PLAY", shift=i))
    assert t.detect_no_progress(6)
    t.record_content(els("LEVELS"))
    assert not t.detect_no_progress(6)


def test_dynamic_values_are_ignored():
    t = StateGraphTracker(run_id=0)
    assert t.compute_content_hash(els("PLAY", "12:30")) == t.compute_content_hash(els("PLAY", "12:31"))
