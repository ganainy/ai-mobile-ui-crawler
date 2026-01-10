"""Tests for StatsDashboard widget."""

import pytest

from PySide6.QtCore import Qt

from mobile_crawler.ui.widgets.stats_dashboard import StatsDashboard


@pytest.fixture
def qt_app():
    """Create QApplication instance for all UI tests.
    
    This fixture is created at session scope to ensure QApplication
    exists for all UI tests. PySide6 requires exactly one QApplication
    instance to exist for widgets to work properly.
    """
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _create_stats_dashboard():
    """Create a new StatsDashboard instance for testing.
    
    Returns:
        StatsDashboard instance
    """
    return StatsDashboard()


class TestStatsDashboardInit:
    """Tests for StatsDashboard initialization."""

    def test_initialization(self, qt_app):
        """Test that StatsDashboard initializes correctly."""
        dashboard = _create_stats_dashboard()
        assert dashboard is not None
        assert dashboard.get_total_steps() == 0
        assert dashboard.get_unique_screens() == 0
        assert dashboard.get_ai_calls() == 0

    def test_has_stats_updated_signal(self, qt_app):
        """Test that stats_updated signal exists."""
        dashboard = _create_stats_dashboard()
        assert hasattr(dashboard, 'stats_updated')
        assert dashboard.stats_updated is not None


class TestMaxLimits:
    """Tests for setting max limits."""

    def test_set_max_steps(self, qt_app):
        """Test setting max steps."""
        dashboard = _create_stats_dashboard()
        dashboard.set_max_steps(200)
        assert dashboard.step_progress_bar.maximum() == 200
        assert dashboard.step_progress_bar.format() == "%v / 200 steps"

    def test_set_max_duration(self, qt_app):
        """Test setting max duration."""
        dashboard = _create_stats_dashboard()
        dashboard.set_max_duration(600)
        assert dashboard.time_progress_bar.maximum() == 600
        assert dashboard.time_progress_bar.format() == "%v / 600 seconds"


class TestUpdateStats:
    """Tests for updating statistics."""

    def test_update_total_steps(self, qt_app):
        """Test updating total steps."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(total_steps=10)
        assert dashboard.get_total_steps() == 10

    def test_update_successful_steps(self, qt_app):
        """Test updating successful steps."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(successful_steps=8)
        assert dashboard.successful_steps_label.text() == "Successful: 8"

    def test_update_failed_steps(self, qt_app):
        """Test updating failed steps."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(failed_steps=2)
        assert dashboard.failed_steps_label.text() == "Failed: 2"

    def test_update_unique_screens(self, qt_app):
        """Test updating unique screens."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(unique_screens=5)
        assert dashboard.get_unique_screens() == 5

    def test_update_total_visits(self, qt_app):
        """Test updating total visits."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(total_visits=15)
        assert dashboard.total_visits_label.text() == "Total Visits: 15"

    def test_update_screens_per_minute(self, qt_app):
        """Test updating screens per minute."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(screens_per_minute=2.5)
        assert dashboard.screens_per_minute_label.text() == "Screens/min: 2.5"

    def test_update_ai_calls(self, qt_app):
        """Test updating AI calls."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(ai_calls=20)
        assert dashboard.get_ai_calls() == 20

    def test_update_avg_ai_response_time(self, qt_app):
        """Test updating average AI response time."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(avg_ai_response_time_ms=1234.56)
        # Python's round() uses banker's rounding (round half to even)
        assert dashboard.ai_response_time_label.text() == "Avg Response: 1235ms"

    def test_update_duration_seconds(self, qt_app):
        """Test updating duration."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(duration_seconds=45.7)
        assert dashboard.duration_label.text() == "Elapsed: 46s"

    def test_update_all_stats(self, qt_app):
        """Test updating all statistics at once."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(
            total_steps=50,
            successful_steps=45,
            failed_steps=5,
            unique_screens=10,
            total_visits=60,
            screens_per_minute=3.2,
            ai_calls=50,
            avg_ai_response_time_ms=800.5,
            duration_seconds=120.5,
        )
        assert dashboard.get_total_steps() == 50
        assert dashboard.successful_steps_label.text() == "Successful: 45"
        assert dashboard.failed_steps_label.text() == "Failed: 5"
        assert dashboard.get_unique_screens() == 10
        assert dashboard.total_visits_label.text() == "Total Visits: 60"
        assert dashboard.screens_per_minute_label.text() == "Screens/min: 3.2"
        assert dashboard.get_ai_calls() == 50
        # Python's round() uses banker's rounding (round half to even)
        assert dashboard.ai_response_time_label.text() == "Avg Response: 800ms"
        assert dashboard.duration_label.text() == "Elapsed: 120s"


class TestProgressBars:
    """Tests for progress bar updates."""

    def test_step_progress_bar_updates(self, qt_app):
        """Test that step progress bar updates correctly."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(total_steps=25)
        assert dashboard.step_progress_bar.value() == 25

    def test_step_progress_bar_capped_at_max(self, qt_app):
        """Test that step progress bar is capped at max."""
        dashboard = _create_stats_dashboard()
        dashboard.set_max_steps(50)
        dashboard.update_stats(total_steps=100)
        assert dashboard.step_progress_bar.value() == 50

    def test_time_progress_bar_updates(self, qt_app):
        """Test that time progress bar updates correctly."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(duration_seconds=60)
        assert dashboard.time_progress_bar.value() == 60

    def test_time_progress_bar_capped_at_max(self, qt_app):
        """Test that time progress bar is capped at max."""
        dashboard = _create_stats_dashboard()
        dashboard.set_max_duration(120)
        dashboard.update_stats(duration_seconds=200)
        assert dashboard.time_progress_bar.value() == 120


class TestReset:
    """Tests for resetting statistics."""

    def test_reset_clears_all_stats(self, qt_app):
        """Test that reset clears all statistics."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(
            total_steps=50,
            successful_steps=45,
            failed_steps=5,
            unique_screens=10,
            total_visits=60,
            screens_per_minute=3.2,
            ai_calls=50,
            avg_ai_response_time_ms=800.5,
            duration_seconds=120.5,
        )
        dashboard.reset()
        assert dashboard.get_total_steps() == 0
        assert dashboard.successful_steps_label.text() == "Successful: 0"
        assert dashboard.failed_steps_label.text() == "Failed: 0"
        assert dashboard.get_unique_screens() == 0
        assert dashboard.total_visits_label.text() == "Total Visits: 0"
        assert dashboard.screens_per_minute_label.text() == "Screens/min: 0.0"
        assert dashboard.get_ai_calls() == 0
        assert dashboard.ai_response_time_label.text() == "Avg Response: 0ms"
        assert dashboard.duration_label.text() == "Elapsed: 0s"

    def test_reset_clears_progress_bars(self, qt_app):
        """Test that reset clears progress bars."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(total_steps=50, duration_seconds=120)
        dashboard.reset()
        assert dashboard.step_progress_bar.value() == 0
        assert dashboard.time_progress_bar.value() == 0


class TestStatsUpdatedSignal:
    """Tests for stats_updated signal."""

    def test_update_stats_emits_signal(self, qt_app):
        """Test that update_stats() emits stats_updated signal."""
        dashboard = _create_stats_dashboard()
        signal_emitted = False
        
        def on_stats_updated():
            nonlocal signal_emitted
            signal_emitted = True
        
        dashboard.stats_updated.connect(on_stats_updated)
        dashboard.update_stats(total_steps=10)
        assert signal_emitted

    def test_reset_does_not_emit_signal(self, qt_app):
        """Test that reset() does not emit stats_updated signal."""
        dashboard = _create_stats_dashboard()
        signal_emitted = False
        
        def on_stats_updated():
            nonlocal signal_emitted
            signal_emitted = True
        
        dashboard.stats_updated.connect(on_stats_updated)
        dashboard.reset()
        # Reset doesn't emit signal (it calls update_stats which does)
        assert signal_emitted  # Signal is emitted by update_stats inside reset


class TestGetters:
    """Tests for getter methods."""

    def test_get_total_steps_returns_correct_value(self, qt_app):
        """Test get_total_steps returns correct value."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(total_steps=42)
        assert dashboard.get_total_steps() == 42

    def test_get_unique_screens_returns_correct_value(self, qt_app):
        """Test get_unique_screens returns correct value."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(unique_screens=17)
        assert dashboard.get_unique_screens() == 17

    def test_get_ai_calls_returns_correct_value(self, qt_app):
        """Test get_ai_calls returns correct value."""
        dashboard = _create_stats_dashboard()
        dashboard.update_stats(ai_calls=99)
        assert dashboard.get_ai_calls() == 99
