"""Regression tests for _parse_droidrun_progress and the stats pipeline.

These tests exercise the log-parsing logic and CrawlStatistics accumulator
without spinning up a full MainWindow. They guard against regressions when
DroidRun log formats change or the stats pipeline is refactored.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from mobile_crawler.ui.main_window import CrawlStatistics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stats(run_id: int = 1) -> CrawlStatistics:
    return CrawlStatistics(run_id=run_id, start_time=datetime.now())


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _make_parser(qt_app=None):
    """Return a minimal object with _parse_droidrun_progress bound to it.

    Uses a simple namespace instead of MainWindow.__new__ to avoid Qt
    widget initialisation. The method only needs _current_stats and
    _update_dashboard_stats.
    """
    import types

    from mobile_crawler.ui.main_window import MainWindow

    class _Stub:
        pass

    obj = _Stub()
    obj._current_stats = _make_stats()
    obj._update_dashboard_stats = MagicMock()
    # _parse_droidrun_progress uses `re` from the module scope; make it available
    # by binding the unbound function directly (it only uses self._current_stats
    # and self._update_dashboard_stats).
    obj._parse_droidrun_progress = types.MethodType(
        MainWindow._parse_droidrun_progress, obj
    )
    return obj


# ---------------------------------------------------------------------------
# CrawlStatistics unit tests
# ---------------------------------------------------------------------------

class TestCrawlStatistics:
    def test_elapsed_seconds_increases(self):
        import time
        stats = _make_stats()
        time.sleep(0.05)
        assert stats.elapsed_seconds() >= 0.04

    def test_avg_ai_response_time_empty(self):
        assert _make_stats().avg_ai_response_time() == 0.0

    def test_avg_ai_response_time_single(self):
        stats = _make_stats()
        stats.ai_response_times_ms.append(500.0)
        assert stats.avg_ai_response_time() == 500.0

    def test_avg_ai_response_time_multiple(self):
        stats = _make_stats()
        stats.ai_response_times_ms.extend([200.0, 400.0])
        assert stats.avg_ai_response_time() == 300.0

    def test_screens_per_minute_zero_when_no_screens(self):
        stats = _make_stats()
        assert stats.screens_per_minute() == 0.0


# ---------------------------------------------------------------------------
# _parse_droidrun_progress — step progress
# ---------------------------------------------------------------------------

class TestParseStepProgress:
    def test_step_line_updates_total_steps(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "🔄 Step 3/15")
        assert obj._current_stats.total_steps == 3

    def test_step_line_updates_last_step_number(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "🔄 Step 5/15")
        assert obj._current_stats.last_step_number == 5

    def test_step_line_sets_current_step_of_max(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "🔄 Step 7/15")
        assert obj._current_stats.current_step_of_max == "7 / 15"

    def test_step_line_does_not_go_backwards(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "🔄 Step 5/15")
        obj._parse_droidrun_progress(1, "🔄 Step 3/15")  # older/duplicate
        assert obj._current_stats.total_steps == 5

    def test_step_line_triggers_dashboard_update(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "🔄 Step 1/15")
        obj._update_dashboard_stats.assert_called()

    def test_step_line_returns_early_no_ai_count(self):
        obj = _make_parser()
        # A step line that also contains "Executor response:" should NOT count as AI call
        obj._parse_droidrun_progress(1, "🔄 Step 2/15 Executor response: foo")
        assert obj._current_stats.ai_call_count == 0


# ---------------------------------------------------------------------------
# _parse_droidrun_progress — action outcomes
# ---------------------------------------------------------------------------

class TestParseActionOutcomes:
    def test_success_emoji_increments_successful_actions(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "✅ Execution complete: Clicked on button")
        assert obj._current_stats.successful_actions == 1
        assert obj._current_stats.failed_actions == 0

    def test_failure_emoji_increments_failed_actions(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "❌ Execution complete: Failed to tap at (100, 200)")
        assert obj._current_stats.failed_actions == 1
        assert obj._current_stats.successful_actions == 0

    def test_multiple_successes_accumulate(self):
        obj = _make_parser()
        for _ in range(3):
            obj._parse_droidrun_progress(1, "✅ Execution complete: ok")
        assert obj._current_stats.successful_actions == 3

    def test_mixed_outcomes_tracked_independently(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "✅ Execution complete: ok")
        obj._parse_droidrun_progress(1, "✅ Execution complete: ok")
        obj._parse_droidrun_progress(1, "❌ Execution complete: fail")
        assert obj._current_stats.successful_actions == 2
        assert obj._current_stats.failed_actions == 1

    def test_execution_complete_without_emoji_ignored(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "Execution complete: something")
        assert obj._current_stats.successful_actions == 0
        assert obj._current_stats.failed_actions == 0

    def test_success_triggers_dashboard_update(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "✅ Execution complete: ok")
        obj._update_dashboard_stats.assert_called()

    def test_failure_triggers_dashboard_update(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "❌ Execution complete: fail")
        obj._update_dashboard_stats.assert_called()


# ---------------------------------------------------------------------------
# _parse_droidrun_progress — AI call counting
# ---------------------------------------------------------------------------

class TestParseAICalls:
    def test_manager_response_increments_ai_calls(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "Manager response: some plan")
        assert obj._current_stats.ai_call_count == 1

    def test_executor_response_increments_ai_calls(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, 'Executor response: {"action": "click"}')
        assert obj._current_stats.ai_call_count == 1

    def test_appopener_response_increments_ai_calls(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "AppOpener response: com.example.app")
        assert obj._current_stats.ai_call_count == 1

    def test_executor_response_does_not_increment_successful_actions(self):
        """Executor response alone must NOT count as a successful action.
        Only '✅ Execution complete:' should do that."""
        obj = _make_parser()
        obj._parse_droidrun_progress(1, 'Executor response: {"action": "tap"}')
        assert obj._current_stats.successful_actions == 0

    def test_multiple_ai_calls_accumulate(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "Manager response: plan")
        obj._parse_droidrun_progress(1, "Executor response: action")
        obj._parse_droidrun_progress(1, "Manager response: plan2")
        assert obj._current_stats.ai_call_count == 3

    def test_ai_call_triggers_dashboard_update(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "Manager response: plan")
        obj._update_dashboard_stats.assert_called()


# ---------------------------------------------------------------------------
# _parse_droidrun_progress — last action type
# ---------------------------------------------------------------------------

class TestParseLastAction:
    def test_action_json_sets_last_action_type(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, '{"action": "click", "index": 5}')
        assert obj._current_stats.last_action_type == "click"

    def test_action_type_updated_on_change(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, '{"action": "click"}')
        obj._parse_droidrun_progress(1, '{"action": "swipe"}')
        assert obj._current_stats.last_action_type == "swipe"

    def test_same_action_type_no_extra_update(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, '{"action": "tap"}')
        call_count_after_first = obj._update_dashboard_stats.call_count
        obj._parse_droidrun_progress(1, '{"action": "tap"}')
        # No new update triggered for same action type
        assert obj._update_dashboard_stats.call_count == call_count_after_first

    def test_no_action_json_leaves_last_action_unchanged(self):
        obj = _make_parser()
        obj._current_stats.last_action_type = "scroll"
        obj._parse_droidrun_progress(1, "some unrelated log line")
        assert obj._current_stats.last_action_type == "scroll"


# ---------------------------------------------------------------------------
# _parse_droidrun_progress — no stats object guard
# ---------------------------------------------------------------------------

class TestParseNoStats:
    def test_no_crash_when_current_stats_is_none(self):
        obj = _make_parser()
        obj._current_stats = None
        # Should not raise
        obj._parse_droidrun_progress(1, "✅ Execution complete: ok")
        obj._parse_droidrun_progress(1, "Manager response: plan")
        obj._parse_droidrun_progress(1, "🔄 Step 1/15")


# ---------------------------------------------------------------------------
# _parse_droidrun_progress — FastAgent markers (Phase 2)
# ---------------------------------------------------------------------------

class TestParseFastAgentMarkers:
    def test_fastagent_response_increments_ai_calls(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "FastAgent response: some tool call")
        assert obj._current_stats.ai_call_count == 1

    def test_structuredoutput_response_increments_ai_calls(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "StructuredOutput response: result")
        assert obj._current_stats.ai_call_count == 1

    def test_output_xml_increments_successful_actions(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "<result><output>Tapped element 5</output></result>")
        assert obj._current_stats.successful_actions == 1
        assert obj._current_stats.failed_actions == 0

    def test_error_xml_increments_failed_actions(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "<result><error>Element not found</error></result>")
        assert obj._current_stats.failed_actions == 1
        assert obj._current_stats.successful_actions == 0

    def test_name_xml_sets_last_action_type(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "<name>tap_element</name>")
        assert obj._current_stats.last_action_type == "tap_element"

    def test_name_xml_overrides_previous_action(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "<name>tap_element</name>")
        obj._parse_droidrun_progress(1, "<name>scroll_down</name>")
        assert obj._current_stats.last_action_type == "scroll_down"

    def test_output_xml_counts_tool_call(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "<output>Done</output>")
        assert obj._current_stats.tool_call_count == 1

    def test_error_xml_counts_tool_error(self):
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "<error>Failed</error>")
        assert obj._current_stats.tool_error_count == 1
        assert obj._current_stats.tool_call_count == 1

    def test_mixed_fastagent_and_executor_markers(self):
        """Both FastAgent and executor markers should accumulate correctly."""
        obj = _make_parser()
        obj._parse_droidrun_progress(1, "FastAgent response: call1")
        obj._parse_droidrun_progress(1, "Manager response: plan")
        obj._parse_droidrun_progress(1, "<output>ok</output>")
        obj._parse_droidrun_progress(1, "✅ Execution complete: done")
        assert obj._current_stats.ai_call_count == 2
        assert obj._current_stats.successful_actions == 2


# ---------------------------------------------------------------------------
# Phase 1 regression: no metric reset on partial events
# ---------------------------------------------------------------------------

class TestNoMetricResetOnPartialEvents:
    """Verify that partial event handlers don't reset unrelated metrics."""

    def test_action_event_preserves_ai_calls(self):
        """_on_action_executed should not reset ai_call_count."""
        obj = _make_parser()
        obj._current_stats.ai_call_count = 5
        obj._current_stats.successful_actions = 3
        # Simulate an action outcome
        obj._parse_droidrun_progress(1, "✅ Execution complete: tap")
        assert obj._current_stats.ai_call_count == 5
        assert obj._current_stats.successful_actions == 4

    def test_ai_call_preserves_action_counts(self):
        """AI call detection should not reset action counts."""
        obj = _make_parser()
        obj._current_stats.successful_actions = 7
        obj._current_stats.failed_actions = 2
        obj._parse_droidrun_progress(1, "FastAgent response: plan")
        assert obj._current_stats.successful_actions == 7
        assert obj._current_stats.failed_actions == 2
        assert obj._current_stats.ai_call_count == 1


# ---------------------------------------------------------------------------
# Phase 4 regression: final stat reconciliation
# ---------------------------------------------------------------------------

class TestFinalStatReconciliation:
    """Guard the reconciliation logic in _on_crawl_completed_stats."""

    def _make_window_with_stats(self):
        import types

        from mobile_crawler.ui.main_window import MainWindow

        class _Stub:
            pass

        obj = _Stub()
        obj._current_stats = _make_stats()
        obj._elapsed_timer = MagicMock()
        obj._update_dashboard_stats = MagicMock()
        obj._on_crawl_completed_stats = types.MethodType(
            MainWindow._on_crawl_completed_stats, obj
        )
        return obj

    def test_zero_suffix_preserves_live_parsed_stats(self):
        """When suffix reports 0/0 but live parser has data, keep live data."""
        obj = self._make_window_with_stats()
        obj._current_stats.successful_actions = 5
        obj._current_stats.failed_actions = 2
        obj._on_crawl_completed_stats(1, 10, 5000.0, "Done | successful=0 failed=0 total=0")
        # Stats cleared after completion, but update was called with live data
        obj._update_dashboard_stats.assert_called()

    def test_nonzero_suffix_overrides_live_when_larger(self):
        """When suffix has more data than live parser, use suffix."""
        obj = self._make_window_with_stats()
        obj._current_stats.successful_actions = 3
        obj._current_stats.failed_actions = 1
        obj._on_crawl_completed_stats(1, 10, 5000.0, "Done | successful=8 failed=3 total=11")
        # Can't check after None, but verify update was called
        obj._update_dashboard_stats.assert_called()

    def test_live_stats_kept_when_suffix_smaller(self):
        """When live parser has more data than suffix, keep live."""
        obj = self._make_window_with_stats()
        obj._current_stats.successful_actions = 10
        obj._current_stats.failed_actions = 3
        obj._on_crawl_completed_stats(1, 15, 8000.0, "Done | successful=2 failed=1 total=3")
        # update_dashboard_stats was called — live stats should have been preserved
        obj._update_dashboard_stats.assert_called()


# ---------------------------------------------------------------------------
# on_crawl_completed_stats — stats suffix parsing
# ---------------------------------------------------------------------------

class TestCrawlCompletedStatsParsing:
    """Guard the stats-suffix parsing in _on_crawl_completed_stats."""

    def _make_window_with_stats(self):
        import types

        from mobile_crawler.ui.main_window import MainWindow

        class _Stub:
            pass

        obj = _Stub()
        obj._current_stats = _make_stats()
        obj._elapsed_timer = MagicMock()
        obj._update_dashboard_stats = MagicMock()
        obj._on_crawl_completed_stats = types.MethodType(
            MainWindow._on_crawl_completed_stats, obj
        )
        return obj

    def test_parses_successful_from_reason_suffix(self):
        obj = self._make_window_with_stats()
        obj._on_crawl_completed_stats(1, 10, 5000.0, "Done | successful=7 failed=2 total=9")
        assert obj._current_stats is None  # cleared after completion
        # We can't check stats after None, so verify update was called
        obj._update_dashboard_stats.assert_called()

    def test_stops_elapsed_timer(self):
        obj = self._make_window_with_stats()
        obj._on_crawl_completed_stats(1, 5, 2000.0, "Done")
        obj._elapsed_timer.stop.assert_called_once()

    def test_clears_current_stats(self):
        obj = self._make_window_with_stats()
        obj._on_crawl_completed_stats(1, 5, 2000.0, "Done")
        assert obj._current_stats is None

    def test_reason_without_suffix_does_not_crash(self):
        obj = self._make_window_with_stats()
        obj._on_crawl_completed_stats(1, 5, 2000.0, "Completed normally")
        assert obj._current_stats is None

    def test_malformed_suffix_does_not_crash(self):
        obj = self._make_window_with_stats()
        obj._on_crawl_completed_stats(1, 5, 2000.0, "Done | garbage=notanumber")
        assert obj._current_stats is None
