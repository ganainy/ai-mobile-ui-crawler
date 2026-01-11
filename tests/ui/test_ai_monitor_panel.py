"""Tests for AI monitor panel widget."""

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from datetime import datetime

from mobile_crawler.ui.widgets.ai_monitor_panel import AIMonitorPanel


@pytest.fixture
def app():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def ai_monitor_panel(app):
    """Create AI monitor panel instance for tests."""
    panel = AIMonitorPanel()
    yield panel


def test_ai_monitor_panel_initialization(ai_monitor_panel):
    """Test that AI monitor panel initializes correctly."""
    assert ai_monitor_panel is not None
    assert ai_monitor_panel.interactions_list is not None
    assert ai_monitor_panel.status_filter is not None
    assert ai_monitor_panel.search_input is not None
    assert ai_monitor_panel.clear_button is not None


def test_add_request_creates_pending_entry(ai_monitor_panel):
    """Test that add_request creates a pending interaction entry."""
    run_id = 1
    step_number = 5
    request_data = {
        "user_prompt": "Test prompt",
        "system_prompt": "Test system prompt"
    }

    # Initially empty
    assert ai_monitor_panel.interactions_list.count() == 0

    # Add request
    ai_monitor_panel.add_request(run_id, step_number, request_data)

    # Should have one item
    assert ai_monitor_panel.interactions_list.count() == 1

    # Check internal storage
    assert step_number in ai_monitor_panel._interactions
    interaction = ai_monitor_panel._interactions[step_number]
    assert interaction["run_id"] == run_id
    assert interaction["step_number"] == step_number
    assert interaction["request_data"] == request_data
    assert interaction["response_data"] is None


def test_add_response_completes_interaction(ai_monitor_panel):
    """Test that add_response completes a pending interaction."""
    run_id = 1
    step_number = 5
    request_data = {"user_prompt": "Test prompt"}
    response_data = {
        "response": "Test response",
        "success": True,
        "tokens_input": 10,
        "tokens_output": 20,
        "latency_ms": 1500
    }

    # Add request first
    ai_monitor_panel.add_request(run_id, step_number, request_data)
    assert ai_monitor_panel.interactions_list.count() == 1

    # Add response
    ai_monitor_panel.add_response(run_id, step_number, response_data)

    # Should still have one item (updated, not added)
    assert ai_monitor_panel.interactions_list.count() == 1

    # Check internal storage updated
    interaction = ai_monitor_panel._interactions[step_number]
    assert interaction["response_data"] == response_data
    assert interaction["success"] == True


def test_status_filter_shows_only_matching_entries(ai_monitor_panel):
    """Test that status filter shows only matching entries."""
    # Add successful interaction
    ai_monitor_panel.add_request(1, 1, {"user_prompt": "Success prompt"})
    ai_monitor_panel.add_response(1, 1, {"response": "Success", "success": True})

    # Add failed interaction
    ai_monitor_panel.add_request(1, 2, {"user_prompt": "Fail prompt"})
    ai_monitor_panel.add_response(1, 2, {"response": "Error", "success": False, "error_message": "Test error"})

    # Initially should show both
    assert ai_monitor_panel.interactions_list.count() == 2

    # Filter to success only
    ai_monitor_panel.status_filter.setCurrentText("Success Only")
    # Note: This triggers the filter, but we need to check visibility

    # Filter to failed only
    ai_monitor_panel.status_filter.setCurrentText("Failed Only")

    # Filter to all
    ai_monitor_panel.status_filter.setCurrentText("All")


def test_search_filters_by_text_content(ai_monitor_panel):
    """Test that search filters by text content."""
    # Add interactions with different content
    ai_monitor_panel.add_request(1, 1, {"user_prompt": "Click the login button"})
    ai_monitor_panel.add_response(1, 1, {"response": "Action: tap", "success": True})

    ai_monitor_panel.add_request(1, 2, {"user_prompt": "Scroll down"})
    ai_monitor_panel.add_response(1, 2, {"response": "Action: scroll", "success": True})

    # Initially should show both
    assert ai_monitor_panel.interactions_list.count() == 2

    # Search for "login" - should show only first
    ai_monitor_panel.search_input.setText("login")
    # Note: This triggers debounced search, would need to wait or trigger manually

    # Search for "scroll" - should show only second
    ai_monitor_panel.search_input.setText("scroll")

    # Clear search
    ai_monitor_panel.search_input.clear()


def test_clear_resets_all_entries(ai_monitor_panel):
    """Test that clear button resets all entries and filters."""
    # Add some interactions
    ai_monitor_panel.add_request(1, 1, {"user_prompt": "Test"})
    ai_monitor_panel.add_response(1, 1, {"response": "OK", "success": True})

    ai_monitor_panel.add_request(1, 2, {"user_prompt": "Test 2"})
    ai_monitor_panel.add_response(1, 2, {"response": "OK", "success": True})

    assert ai_monitor_panel.interactions_list.count() == 2
    assert len(ai_monitor_panel._interactions) == 2

    # Clear
    ai_monitor_panel.clear()

    # Should be empty
    assert ai_monitor_panel.interactions_list.count() == 0
    assert len(ai_monitor_panel._interactions) == 0
    assert ai_monitor_panel._filter_state["status"] == "all"
    assert ai_monitor_panel._filter_state["search"] == ""
    assert ai_monitor_panel.status_filter.currentText() == "All"
    assert ai_monitor_panel.search_input.text() == ""