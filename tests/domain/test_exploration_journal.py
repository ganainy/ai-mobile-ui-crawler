"""Tests for ExplorationJournal."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from mobile_crawler.domain.exploration_journal import ExplorationJournal, JournalEntry
from mobile_crawler.infrastructure.step_log_repository import StepLog


class TestExplorationJournal:
    """Tests for ExplorationJournal."""

    def test_init(self):
        """Test initialization."""
        mock_repo = Mock()
        journal = ExplorationJournal(mock_repo)
        assert journal._step_log_repository is mock_repo

    def test_get_entries_success(self):
        """Test successful retrieval of journal entries."""
        mock_repo = Mock()
        mock_repo.get_exploration_journal.return_value = [
            StepLog(
                id=1,
                run_id=100,
                step_number=1,
                timestamp=datetime(2026, 1, 10, 0, 0),
                from_screen_id=1,
                to_screen_id=2,
                action_type="click",
                action_description="Clicked button",
                target_bbox_json='{"top_left": [0, 0], "bottom_right": [100, 100]}',
                input_text=None,
                execution_success=True,
                error_message=None,
                action_duration_ms=500.0,
                ai_response_time_ms=1000.0,
                ai_reasoning="Found button"
            ),
            StepLog(
                id=2,
                run_id=100,
                step_number=2,
                timestamp=datetime(2026, 1, 10, 0, 1),
                from_screen_id=2,
                to_screen_id=3,
                action_type="scroll_down",
                action_description="Scrolled down",
                target_bbox_json=None,
                input_text=None,
                execution_success=True,
                error_message=None,
                action_duration_ms=300.0,
                ai_response_time_ms=800.0,
                ai_reasoning="Need to see more"
            ),
        ]

        journal = ExplorationJournal(mock_repo)
        entries = journal.get_entries(run_id=100, limit=10)

        assert len(entries) == 2
        assert entries[0].step_number == 1
        assert entries[0].from_screen_id == 1
        assert entries[0].action_type == "click"
        assert entries[1].step_number == 2
        assert entries[1].action_type == "scroll_down"

    def test_get_entries_with_limit(self):
        """Test limiting number of entries."""
        mock_repo = Mock()
        mock_repo.get_exploration_journal.return_value = [
            StepLog(id=i, run_id=100, step_number=i, timestamp=datetime.now(),
                      from_screen_id=i, to_screen_id=i+1, action_type="click",
                      action_description=None, target_bbox_json=None, input_text=None,
                      execution_success=True, error_message=None, action_duration_ms=None,
                      ai_response_time_ms=None, ai_reasoning=None)
            for i in range(5)
        ]

        journal = ExplorationJournal(mock_repo)
        entries = journal.get_entries(run_id=100, limit=5)

        assert len(entries) == 5
        assert entries[0].step_number == 0
        assert entries[4].step_number == 4

    def test_get_entries_empty(self):
        """Test empty journal entries."""
        mock_repo = Mock()
        mock_repo.get_exploration_journal.return_value = []

        journal = ExplorationJournal(mock_repo)
        entries = journal.get_entries(run_id=100)

        assert entries == []

    def test_get_entries_repository_error(self):
        """Test handling repository error."""
        mock_repo = Mock()
        mock_repo.get_exploration_journal.side_effect = Exception("Database error")

        journal = ExplorationJournal(mock_repo)
        entries = journal.get_entries(run_id=100)

        assert entries == []

    def test_get_formatted_entries_success(self):
        """Test formatting of successful entries."""
        mock_repo = Mock()
        mock_repo.get_exploration_journal.return_value = [
            StepLog(
                id=1,
                run_id=100,
                step_number=1,
                timestamp=datetime.now(),
                from_screen_id=1,
                to_screen_id=2,
                action_type="click",
                action_description="Clicked submit button",
                target_bbox_json='{"x": 100}',
                input_text=None,
                execution_success=True,
                error_message=None,
                action_duration_ms=500.0,
                ai_response_time_ms=1000.0,
                ai_reasoning="Button found"
            ),
            StepLog(
                id=2,
                run_id=100,
                step_number=2,
                timestamp=datetime.now(),
                from_screen_id=2,
                to_screen_id=3,
                action_type="input",
                action_description="Entered text",
                target_bbox_json=None,
                input_text="test",
                execution_success=False,
                error_message="Element not found",
                action_duration_ms=None,
                ai_response_time_ms=None,
                ai_reasoning=None
            ),
        ]

        journal = ExplorationJournal(mock_repo)
        formatted = journal.get_formatted_entries(run_id=100)

        assert "Step 1: click (Clicked submit button) - ✓" in formatted
        assert "Step 2: input (Entered text) - ✗ (Element not found)" in formatted

    def test_get_formatted_entries_with_target_element(self):
        """Test formatting with target element."""
        mock_repo = Mock()
        mock_repo.get_exploration_journal.return_value = [
            StepLog(
                id=1,
                run_id=100,
                step_number=1,
                timestamp=datetime.now(),
                from_screen_id=1,
                to_screen_id=2,
                action_type="click",
                action_description=None,
                target_bbox_json='{"id": "submit_btn"}',
                input_text=None,
                execution_success=True,
                error_message=None,
                action_duration_ms=500.0,
                ai_response_time_ms=1000.0,
                ai_reasoning=None
            ),
        ]

        journal = ExplorationJournal(mock_repo)
        formatted = journal.get_formatted_entries(run_id=100)

        assert "Step 1: click on submit_btn - ✓" in formatted
        assert "submit_btn" in formatted

    def test_get_formatted_entries_empty(self):
        """Test formatting of empty entries."""
        mock_repo = Mock()
        mock_repo.get_exploration_journal.return_value = []

        journal = ExplorationJournal(mock_repo)
        formatted = journal.get_formatted_entries(run_id=100)

        assert formatted == "No exploration history available."

    def test_get_formatted_entries_default_limit(self):
        """Test default limit of 15 entries."""
        mock_repo = Mock()
        mock_repo.get_exploration_journal.return_value = [
            StepLog(id=i, run_id=100, step_number=i, timestamp=datetime.now(),
                      from_screen_id=i, to_screen_id=i+1, action_type="click",
                      action_description=None, target_bbox_json=None, input_text=None,
                      execution_success=True, error_message=None, action_duration_ms=None,
                      ai_response_time_ms=None, ai_reasoning=None)
            for i in range(10)
        ]

        journal = ExplorationJournal(mock_repo)
        # Should use default limit of 15
        entries = journal.get_entries(run_id=100)

        assert len(entries) == 10

    def test_get_formatted_entries_multiple_errors(self):
        """Test formatting with multiple error entries."""
        mock_repo = Mock()
        mock_repo.get_exploration_journal.return_value = [
            StepLog(
                id=i,
                run_id=100,
                step_number=i,
                timestamp=datetime.now(),
                from_screen_id=i,
                to_screen_id=i+1,
                action_type="click",
                action_description=None,
                target_bbox_json=None,
                input_text=None,
                execution_success=False,
                error_message=f"Error {i}",
                action_duration_ms=None,
                ai_response_time_ms=None,
                ai_reasoning=None
            )
            for i in range(3)
        ]

        journal = ExplorationJournal(mock_repo)
        formatted = journal.get_formatted_entries(run_id=100)

        assert formatted.count("✗") == 3
        assert "Error 0" in formatted
        assert "Error 1" in formatted
        assert "Error 2" in formatted

    def test_get_entries_with_none_timestamp(self):
        """Test entries with None timestamp."""
        mock_repo = Mock()
        mock_repo.get_exploration_journal.return_value = [
            StepLog(
                id=1,
                run_id=100,
                step_number=1,
                timestamp=None,
                from_screen_id=1,
                to_screen_id=2,
                action_type="click",
                action_description="Click",
                target_bbox_json=None,
                input_text=None,
                execution_success=True,
                error_message=None,
                action_duration_ms=None,
                ai_response_time_ms=None,
                ai_reasoning=None
            ),
        ]

        journal = ExplorationJournal(mock_repo)
        entries = journal.get_entries(run_id=100)

        assert entries[0].timestamp is None

    def test_get_entries_with_none_screen_ids(self):
        """Test entries with None screen IDs."""
        mock_repo = Mock()
        mock_repo.get_exploration_journal.return_value = [
            StepLog(
                id=1,
                run_id=100,
                step_number=1,
                timestamp=datetime.now(),
                from_screen_id=None,
                to_screen_id=None,
                action_type="back",
                action_description="Pressed back",
                target_bbox_json=None,
                input_text=None,
                execution_success=True,
                error_message=None,
                action_duration_ms=None,
                ai_response_time_ms=None,
                ai_reasoning=None
            ),
        ]

        journal = ExplorationJournal(mock_repo)
        entries = journal.get_entries(run_id=100)

        assert entries[0].from_screen_id is None
        assert entries[0].to_screen_id is None
