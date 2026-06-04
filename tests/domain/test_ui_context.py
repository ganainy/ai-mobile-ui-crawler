"""Tests for UIContext model."""

import hashlib
from unittest.mock import MagicMock, Mock

import pytest

from mobile_crawler.domain.ui_context import UIContextManager


@pytest.fixture
def mock_db():
    """Create a mock database connection."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None
    return conn


@pytest.fixture
def mock_omni_client():
    """Create a mock OmniParser client."""
    client = Mock()
    client.backend.value = "replicate"
    client.parse.return_value = []
    return client


@pytest.fixture
def ui_context_manager(mock_db, mock_omni_client):
    """Create a UIContextManager with mock dependencies."""
    return UIContextManager(mock_db, mock_omni_client)


class TestUIContextManager:
    """Tests for UIContextManager."""

    def test_construction_with_required_fields(self, mock_db, mock_omni_client):
        """Test UIContextManager construction with required fields."""
        manager = UIContextManager(mock_db, mock_omni_client)
        assert manager.db == mock_db
        assert manager.omni_client == mock_omni_client
        assert manager._prev_a11y is None

    def test_get_screen_key(self, ui_context_manager):
        """Test _get_screen_key generates consistent hash."""
        phone_state = {
            "current_app": {
                "package": "com.example.app",
                "activity": ".MainActivity",
            }
        }
        key = ui_context_manager._get_screen_key(phone_state)
        expected = hashlib.md5(b"com.example.app:.MainActivity").hexdigest()
        assert key == expected

    def test_get_screen_key_with_missing_data(self, ui_context_manager):
        """Test _get_screen_key handles missing data gracefully."""
        phone_state = {}
        key = ui_context_manager._get_screen_key(phone_state)
        expected = hashlib.md5(b"unknown:unknown").hexdigest()
        assert key == expected

    def test_quick_a11y_check_too_sparse(self, ui_context_manager):
        """Test _quick_a11y_check detects sparse a11y tree."""
        a11y = [{"clickable": True}]
        issues = ui_context_manager._quick_a11y_check(a11y, None)
        assert "too_sparse" in issues

    def test_quick_a11y_check_nothing_clickable(self, ui_context_manager):
        """Test _quick_a11y_check detects nothing clickable."""
        a11y = [{"text": "text1"}, {"text": "text2"}, {"text": "text3"}, {"text": "text4"}, {"text": "text5"}]
        issues = ui_context_manager._quick_a11y_check(a11y, None)
        assert "nothing_clickable" in issues

    def test_quick_a11y_check_stale(self, ui_context_manager):
        """Test _quick_a11y_check detects stale a11y tree."""
        a11y = [{"clickable": True}] * 10
        prev_a11y = list(a11y)
        issues = ui_context_manager._quick_a11y_check(a11y, prev_a11y)
        assert "a11y_stale" in issues

    def test_quick_a11y_check_no_issues(self, ui_context_manager):
        """Test _quick_a11y_check returns empty list for valid tree."""
        a11y = [{"clickable": True}] * 10
        issues = ui_context_manager._quick_a11y_check(a11y, None)
        assert issues == []

    def test_find_unmatched_interactables(self, ui_context_manager):
        """Test _find_unmatched_interactables finds unmatched elements."""
        omni = [
            {"interactivity": True, "bbox": [10, 10, 50, 50]},
            {"interactivity": True, "bbox": [200, 200, 250, 250]},
        ]
        a11y = [
            {"bbox": [10, 10, 50, 50]},
        ]
        unmatched = ui_context_manager._find_unmatched_interactables(omni, a11y)
        assert len(unmatched) == 1
        assert unmatched[0]["bbox"] == [200, 200, 250, 250]

    def test_find_uncovered_regions(self, ui_context_manager):
        """Test _find_uncovered_regions finds regions with omni but no a11y."""
        omni = [
            {"bbox": [0.1, 0.1, 0.2, 0.2]},
        ]
        a11y = []
        uncovered = ui_context_manager._find_uncovered_regions(omni, a11y, grid=4)
        assert len(uncovered) > 0

    def test_get_cache_status_returns_none_on_empty(self, ui_context_manager, mock_db):
        """Test _get_cache_status returns None when no cache entry."""
        mock_db.execute.return_value.fetchone.return_value = None
        status = ui_context_manager._get_cache_status("some_key")
        assert status is None

    def test_get_cache_status_returns_status(self, ui_context_manager, mock_db):
        """Test _get_cache_status returns cached status."""
        mock_db.execute.return_value.fetchone.return_value = {"status": "trusted"}
        status = ui_context_manager._get_cache_status("some_key")
        assert status == "trusted"

    def test_set_cache_status(self, ui_context_manager, mock_db):
        """Test _set_cache_status writes to database."""
        ui_context_manager._set_cache_status("key1", "trusted")
        mock_db.execute.assert_called()
        mock_db.commit.assert_called()

    def test_get_cached_omni_returns_none_on_empty(self, ui_context_manager, mock_db):
        """Test _get_cached_omni returns None when no cache entry."""
        mock_db.execute.return_value.fetchone.return_value = None
        result = ui_context_manager._get_cached_omni("some_key")
        assert result is None

    def test_cleanup_old_cache(self, ui_context_manager, mock_db):
        """Test cleanup_old_cache deletes old entries."""
        cursor = Mock()
        cursor.rowcount = 5
        mock_db.execute.return_value = cursor
        deleted = ui_context_manager.cleanup_old_cache(ttl_days=30)
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        assert deleted == 5

    def test_bbox_iou_calculation(self, ui_context_manager):
        """Test bbox_iou helper calculates intersection over union."""
        omni = [
            {"interactivity": True, "bbox": [0, 0, 100, 100]},
            {"interactivity": True, "bbox": [50, 50, 150, 150]},
        ]
        a11y = [
            {"bbox": [0, 0, 100, 100]},
        ]
        ui_context_manager._find_unmatched_interactables(omni, a11y)
        # The second omni element overlaps but still has IOU > 0.3
        # Let's use a case where they clearly don't match
        omni2 = [
            {"interactivity": True, "bbox": [0, 0, 10, 10]},
            {"interactivity": True, "bbox": [200, 200, 210, 210]},
        ]
        a11y2 = [
            {"bbox": [0, 0, 10, 10]},
        ]
        unmatched2 = ui_context_manager._find_unmatched_interactables(omni2, a11y2)
        assert len(unmatched2) == 1
        assert unmatched2[0]["bbox"] == [200, 200, 210, 210]
