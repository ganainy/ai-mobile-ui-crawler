"""Unit tests for StatsDashboard widget."""

import pytest
from PySide6.QtWidgets import QApplication
from mobile_crawler.ui.widgets.stats_dashboard import StatsDashboard


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestStatsDashboard:
    """Test StatsDashboard widget."""

    def test_update_stats_with_timing(self, qapp):
        """Test updating stats with timing metrics."""
        dashboard = StatsDashboard()
        
        # Update with timing data
        dashboard.update_stats(
            total_steps=5,
            ocr_avg_ms=150.0,
            action_avg_ms=200.0,
            screenshot_avg_ms=50.0
        )
        
        # Check labels
        assert "OCR Avg: 150ms" in dashboard.ocr_avg_label.text()
        assert "Action Avg: 200ms" in dashboard.action_avg_label.text()
        assert "Screenshot Avg: 50ms" in dashboard.screenshot_avg_label.text()

    def test_reset_clears_timing(self, qapp):
        """Test that reset clears timing metrics."""
        dashboard = StatsDashboard()
        
        # Set some data
        dashboard.update_stats(
            total_steps=3,
            ocr_avg_ms=100.0,
            action_avg_ms=150.0,
            screenshot_avg_ms=25.0
        )
        
        # Reset
        dashboard.reset()
        
        # Check timing labels are reset
        assert "OCR Avg: 0ms" in dashboard.ocr_avg_label.text()
        assert "Action Avg: 0ms" in dashboard.action_avg_label.text()
        assert "Screenshot Avg: 0ms" in dashboard.screenshot_avg_label.text()

    def test_timing_display_formatting(self, qapp):
        """Test timing display formatting."""
        dashboard = StatsDashboard()
        
        # Test decimal formatting
        dashboard.update_stats(ocr_avg_ms=123.456)
        assert "OCR Avg: 123ms" in dashboard.ocr_avg_label.text()
        
        # Test zero values
        dashboard.update_stats(ocr_avg_ms=0.0)
        assert "OCR Avg: 0ms" in dashboard.ocr_avg_label.text()