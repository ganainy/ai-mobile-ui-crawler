"""Unit tests for CrawlStatistics dataclass."""

import pytest
from datetime import datetime
from mobile_crawler.ui.main_window import CrawlStatistics


class TestCrawlStatistics:
    """Test CrawlStatistics dataclass methods."""

    def test_avg_ocr_time_ms_with_data(self):
        """Test average OCR time calculation with data."""
        stats = CrawlStatistics(run_id=1, start_time=datetime.now())
        stats.ocr_total_time_ms = 1000.0  # 1 second total
        stats.ocr_operation_count = 2     # 2 operations
        
        assert stats.avg_ocr_time_ms() == 500.0

    def test_avg_ocr_time_ms_no_operations(self):
        """Test average OCR time with no operations."""
        stats = CrawlStatistics(run_id=1, start_time=datetime.now())
        stats.ocr_total_time_ms = 0.0
        stats.ocr_operation_count = 0
        
        assert stats.avg_ocr_time_ms() == 0.0

    def test_avg_action_time_ms_with_data(self):
        """Test average action time calculation with data."""
        stats = CrawlStatistics(run_id=1, start_time=datetime.now())
        stats.action_total_time_ms = 600.0  # 0.6 seconds total
        stats.action_count = 3             # 3 actions
        
        assert stats.avg_action_time_ms() == 200.0

    def test_avg_action_time_ms_no_actions(self):
        """Test average action time with no actions."""
        stats = CrawlStatistics(run_id=1, start_time=datetime.now())
        stats.action_total_time_ms = 0.0
        stats.action_count = 0
        
        assert stats.avg_action_time_ms() == 0.0

    def test_avg_screenshot_time_ms_with_data(self):
        """Test average screenshot time calculation with data."""
        stats = CrawlStatistics(run_id=1, start_time=datetime.now())
        stats.screenshot_total_time_ms = 300.0  # 0.3 seconds total
        stats.screenshot_count = 3               # 3 screenshots
        
        assert stats.avg_screenshot_time_ms() == 100.0

    def test_avg_screenshot_time_ms_no_screenshots(self):
        """Test average screenshot time with no screenshots."""
        stats = CrawlStatistics(run_id=1, start_time=datetime.now())
        stats.screenshot_total_time_ms = 0.0
        stats.screenshot_count = 0
        
        assert stats.avg_screenshot_time_ms() == 0.0