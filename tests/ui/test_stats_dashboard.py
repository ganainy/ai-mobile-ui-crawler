"""Tests for StatsDashboard widget — matches current widget API."""

import pytest
from PySide6.QtWidgets import QApplication

from mobile_crawler.ui.widgets.stats_dashboard import StatsDashboard


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def dashboard(qt_app):
    return StatsDashboard()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestInit:
    def test_creates_without_error(self, dashboard):
        assert dashboard is not None

    def test_initial_total_steps_zero(self, dashboard):
        assert dashboard.get_total_steps() == 0

    def test_placeholder_visible_initially(self, dashboard):
        # isVisible() requires the widget to be shown; use isHidden() instead
        assert not dashboard.placeholder_label.isHidden()
        assert dashboard.stats_content.isHidden()

    def test_has_stats_updated_signal(self, dashboard):
        assert hasattr(dashboard, "stats_updated")


# ---------------------------------------------------------------------------
# set_max_steps / set_max_duration / set_progress_mode
# ---------------------------------------------------------------------------


class TestConfiguration:
    def test_set_max_steps_updates_progress_bar(self, dashboard):
        dashboard.set_max_steps(50)
        assert dashboard.step_progress_bar.maximum() == 50

    def test_set_max_steps_updates_format(self, dashboard):
        dashboard.set_max_steps(30)
        assert "30" in dashboard.step_progress_bar.format()

    def test_set_max_duration_stores_value(self, dashboard):
        dashboard.set_max_duration(600)
        assert dashboard._max_duration_seconds == 600

    def test_progress_mode_duration_switches_bar(self, dashboard):
        dashboard.set_max_duration(300)
        dashboard.set_progress_mode("duration")
        assert dashboard.step_progress_bar.maximum() == 300

    def test_progress_mode_steps_switches_bar_back(self, dashboard):
        dashboard.set_max_steps(20)
        dashboard.set_progress_mode("duration")
        dashboard.set_progress_mode("steps")
        assert dashboard.step_progress_bar.maximum() == 20


# ---------------------------------------------------------------------------
# update_stats — content visibility
# ---------------------------------------------------------------------------


class TestContentVisibility:
    def test_stats_content_shown_when_steps_nonzero(self, dashboard):
        dashboard.update_stats(total_steps=1)
        assert not dashboard.stats_content.isHidden()
        assert dashboard.placeholder_label.isHidden()

    def test_stats_content_shown_when_duration_nonzero(self, dashboard):
        dashboard.update_stats(duration_seconds=5.0)
        assert not dashboard.stats_content.isHidden()


# ---------------------------------------------------------------------------
# update_stats — step progress
# ---------------------------------------------------------------------------


class TestStepProgress:
    def test_total_steps_label(self, dashboard):
        dashboard.update_stats(total_steps=7)
        assert "7" in dashboard.total_steps_label.text()

    def test_step_progress_bar_value(self, dashboard):
        dashboard.set_max_steps(100)
        dashboard.update_stats(total_steps=42)
        assert dashboard.step_progress_bar.value() == 42

    def test_step_progress_bar_capped_at_max(self, dashboard):
        dashboard.set_max_steps(10)
        dashboard.update_stats(total_steps=999)
        assert dashboard.step_progress_bar.value() == 10

    def test_current_step_label_from_step_progress(self, dashboard):
        dashboard.update_stats(step_progress="5 / 15")
        assert "5 / 15" in dashboard.current_step_label.text()

    def test_duration_mode_progress_bar(self, dashboard):
        dashboard.set_max_duration(300)
        dashboard.set_progress_mode("duration")
        dashboard.update_stats(duration_seconds=120.0)
        assert dashboard.step_progress_bar.value() == 120


# ---------------------------------------------------------------------------
# update_stats — Actions section
# ---------------------------------------------------------------------------


class TestActionsSection:
    def test_successful_actions_label(self, dashboard):
        dashboard.update_stats(successful_steps=8)
        assert "8" in dashboard.successful_steps_label.text()

    def test_failed_actions_label(self, dashboard):
        dashboard.update_stats(failed_steps=3)
        assert "3" in dashboard.failed_steps_label.text()

    def test_success_rate_shown_when_actions_present(self, dashboard):
        dashboard.update_stats(successful_steps=9, failed_steps=1)
        assert "90%" in dashboard.success_rate_label.text()

    def test_success_rate_dash_when_no_actions(self, dashboard):
        dashboard.update_stats(successful_steps=0, failed_steps=0)
        assert "—" in dashboard.success_rate_label.text()

    def test_last_action_label(self, dashboard):
        dashboard.update_stats(last_action="tap")
        assert "tap" in dashboard.last_action_label.text()

    def test_last_action_dash_when_empty(self, dashboard):
        dashboard.update_stats(last_action="")
        assert "—" in dashboard.last_action_label.text()

    def test_success_rate_100_percent(self, dashboard):
        dashboard.update_stats(successful_steps=5, failed_steps=0)
        assert "100%" in dashboard.success_rate_label.text()

    def test_success_rate_zero_percent(self, dashboard):
        dashboard.update_stats(successful_steps=0, failed_steps=5)
        assert "0%" in dashboard.success_rate_label.text()


# ---------------------------------------------------------------------------
# update_stats — AI Performance section
# ---------------------------------------------------------------------------


class TestAIPerformanceSection:
    def test_ai_calls_label(self, dashboard):
        dashboard.update_stats(ai_calls=12)
        assert "12" in dashboard.ai_calls_label.text()

    def test_avg_response_shown_when_nonzero(self, dashboard):
        dashboard.update_stats(avg_ai_response_time_ms=2500.0)
        # 2500ms → 2.5s
        assert "2.5s" in dashboard.ai_response_time_label.text()

    def test_avg_response_dash_when_zero(self, dashboard):
        dashboard.update_stats(avg_ai_response_time_ms=0.0)
        assert "—" in dashboard.ai_response_time_label.text()

    def test_ai_calls_zero_initially(self, dashboard):
        assert "0" in dashboard.ai_calls_label.text()


# ---------------------------------------------------------------------------
# update_stats — Duration section
# ---------------------------------------------------------------------------


class TestDurationSection:
    def test_duration_label(self, dashboard):
        dashboard.update_stats(duration_seconds=75.0)
        assert "75" in dashboard.duration_label.text()

    def test_duration_rounds_to_integer(self, dashboard):
        dashboard.update_stats(duration_seconds=45.9)
        assert "46" in dashboard.duration_label.text()


# ---------------------------------------------------------------------------
# get_total_steps
# ---------------------------------------------------------------------------


class TestGetters:
    def test_get_total_steps(self, dashboard):
        dashboard.update_stats(total_steps=33)
        assert dashboard.get_total_steps() == 33

    def test_get_total_steps_zero_initially(self, dashboard):
        assert dashboard.get_total_steps() == 0


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


class TestReset:
    def test_reset_hides_content(self, dashboard):
        dashboard.update_stats(total_steps=5)
        dashboard.reset()
        assert not dashboard.placeholder_label.isHidden()
        assert dashboard.stats_content.isHidden()

    def test_reset_clears_total_steps(self, dashboard):
        dashboard.update_stats(total_steps=10)
        dashboard.reset()
        assert dashboard.get_total_steps() == 0

    def test_reset_clears_progress_bar(self, dashboard):
        dashboard.update_stats(total_steps=50)
        dashboard.reset()
        assert dashboard.step_progress_bar.value() == 0


# ---------------------------------------------------------------------------
# stats_updated signal
# ---------------------------------------------------------------------------


class TestSignal:
    def test_update_stats_emits_signal(self, dashboard):
        fired = []
        dashboard.stats_updated.connect(lambda: fired.append(1))
        dashboard.update_stats(total_steps=1)
        assert fired


# ---------------------------------------------------------------------------
# Live Feed
# ---------------------------------------------------------------------------


class TestLiveFeed:
    def test_first_frame_switches_board_to_live(self, dashboard):
        from PySide6.QtGui import QImage

        assert not dashboard.is_live_showing()
        dashboard.set_live_frame(QImage(32, 64, QImage.Format.Format_RGB888))
        assert dashboard.is_live_showing()

    def test_stop_falls_back_to_static_and_offers_restart(self, dashboard):
        from PySide6.QtGui import QImage

        dashboard.set_live_frame(QImage(32, 64, QImage.Format.Format_RGB888))
        dashboard.stop_live_view("Live feed stopped: boom", offer_restart=True)
        assert not dashboard.is_live_showing()
        assert not dashboard.live_restart_button.isHidden()
        assert "boom" in dashboard.screenshot_hint_label.text()

    def test_overlay_boxes_fade_out(self, dashboard):
        from mobile_crawler.ui.widgets.stats_dashboard import OVERLAY_FADE_SECONDS

        view = dashboard.live_view
        view.set_boxes([{"index": 1, "bounds": "0,0,10,10"}])
        start = view._boxes_set_at
        assert view.overlay_alpha(start) == 1.0
        assert 0 < view.overlay_alpha(start + OVERLAY_FADE_SECONDS / 2) < 1
        assert view.overlay_alpha(start + OVERLAY_FADE_SECONDS) == 0.0

    def test_parse_element_boxes_skips_invalid(self):
        from mobile_crawler.ui.widgets.stats_dashboard import parse_element_boxes

        boxes = parse_element_boxes(
            [
                {"index": 1, "bounds": "1,2,3,4"},
                {"index": 2, "bounds": "bad"},
                {"index": 3, "bounds": "5,5,5,9"},
                {"bounds": "1,2,3,4"},
            ]
        )
        assert boxes == [(1, 1, 2, 3, 4)]

    def test_toggle_signal_emitted(self, dashboard):
        seen = []
        dashboard.live_feed_toggled.connect(seen.append)
        dashboard.live_checkbox.setChecked(False)
        assert seen == [False]
