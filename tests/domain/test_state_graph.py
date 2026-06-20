from mobile_crawler.domain.state_graph import StateGraphTracker


def test_compute_layout_hash_stability():
    tracker = StateGraphTracker(run_id=1)

    # Base layout
    elements = [
        {"className": "Button", "resourceId": "submit_btn", "bounds": "10,20,30,40", "text": "Submit"},
        {"className": "TextView", "resourceId": "title", "bounds": "5,5,100,20", "text": "Welcome"},
    ]

    hash1 = tracker.compute_layout_hash(elements)

    # Adding a clock/battery/status bar dynamic element
    elements_with_clock = elements + [
        {"className": "TextView", "resourceId": "statusBarClock", "bounds": "900,0,1000,20", "text": "10:30 AM"},
        {"className": "TextView", "resourceId": "battery_text", "bounds": "800,0,850,20", "text": "85%"},
    ]

    hash2 = tracker.compute_layout_hash(elements_with_clock)

    # Hashes should be identical because dynamic elements are filtered out
    assert hash1 == hash2


def test_compute_layout_hash_structural_change():
    tracker = StateGraphTracker(run_id=1)

    elements1 = [
        {"className": "Button", "resourceId": "submit_btn", "bounds": "10,20,30,40", "text": "Submit"},
    ]
    hash1 = tracker.compute_layout_hash(elements1)

    elements2 = [
        {"className": "Button", "resourceId": "cancel_btn", "bounds": "10,20,30,40", "text": "Cancel"},
    ]
    hash2 = tracker.compute_layout_hash(elements2)

    # Hashes must differ when stable elements differ
    assert hash1 != hash2


def test_record_state_discovery():
    tracker = StateGraphTracker(run_id=1)

    hash_val = "abc123hash"

    # First time seen
    is_new = tracker.record_state(hash_val, step_number=1, package="com.test.app", activity="MainActivity")
    assert is_new is True
    assert tracker.states[hash_val]["visit_count"] == 1

    # Second time seen
    is_new2 = tracker.record_state(hash_val, step_number=2, package="com.test.app", activity="MainActivity")
    assert is_new2 is False
    assert tracker.states[hash_val]["visit_count"] == 2
    assert tracker.states[hash_val]["last_seen_step"] == 2


def test_loop_detection():
    tracker = StateGraphTracker(run_id=1)

    # Record repeating history of visited hashes: stateA -> stateB -> stateA -> stateB
    state_a = "stateA"
    state_b = "stateB"

    for step in range(1, 9):
        # A, B, A, B, A, B, A, B
        current = state_a if step % 2 == 1 else state_b
        tracker.record_state(current, step, "com.test", "Activity")

    assert tracker.detect_loop(window_size=2) is True


def test_loop_recovery_hint():
    tracker = StateGraphTracker(run_id=1)
    state_a = "stateA"

    # Record some actions
    tracker.record_transition(state_a, "stateB", "click(1)", step_number=1)

    elements = [
        {"index": 1, "text": "Home", "clickable": True},
        {"index": 2, "text": "Settings", "clickable": True},
    ]

    # Clicked index 1 previously, so it should suggest index 2
    hint = tracker.get_loop_recovery_hint(state_a, elements)
    assert "element [2]" in hint
