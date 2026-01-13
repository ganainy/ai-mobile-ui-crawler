import pytest
import os
from unittest.mock import MagicMock, patch
from datetime import datetime
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import Qt

from mobile_crawler.infrastructure.run_repository import Run
from mobile_crawler.ui.widgets.run_history_view import RunHistoryView

@pytest.fixture
def qt_app():
    """Create QApplication instance for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

def test_open_folder_button_enables_with_session_path(qt_app):
    """Test that Open Folder button is enabled when session_path exists."""
    # Mock dependencies
    mock_run_repo = MagicMock()
    mock_report_gen = MagicMock()
    mock_mobsf = MagicMock()
    
    # Create a run with session_path
    run = Run(
        id=1,
        device_id="test_device",
        app_package="com.test",
        start_activity=None,
        start_time=datetime.now(),
        end_time=None,
        status="COMPLETED",
        ai_provider="gemini",
        ai_model="pro",
        session_path="/tmp/fake_session"
    )
    mock_run_repo.get_all_runs.return_value = [run]
    
    # Mock os.path.exists to return True for the session path
    # and provide standard mock for everything else
    with patch('os.path.exists', return_value=True):
        view = RunHistoryView(mock_run_repo, mock_report_gen, mock_mobsf)
        
        # Get the cell widget for actions (column 9)
        open_btn = view.table.cellWidget(0, 9)
        assert isinstance(open_btn, QPushButton)
        assert open_btn.isEnabled()
        assert "Open" in open_btn.text()

def test_open_folder_button_disables_when_no_folder_found(qt_app):
    """Test that Open Folder button is disabled when no folder is found anywhere."""
    # Mock dependencies
    mock_run_repo = MagicMock()
    mock_report_gen = MagicMock()
    mock_mobsf = MagicMock()
    
    # Create a run WITHOUT session_path
    run = Run(
        id=1,
        device_id="test_device",
        app_package="com.test",
        start_activity=None,
        start_time=datetime.now(),
        end_time=None,
        status="COMPLETED",
        ai_provider="gemini",
        ai_model="pro",
        session_path=None
    )
    mock_run_repo.get_all_runs.return_value = [run]
    
    # Mock os.path.exists to return False for everything (no heuristic match either)
    with patch('os.path.exists', return_value=False):
        view = RunHistoryView(mock_run_repo, mock_report_gen, mock_mobsf)
        
        # Get the cell widget for actions (column 9)
        open_btn = view.table.cellWidget(0, 9)
        assert isinstance(open_btn, QPushButton)
        assert not open_btn.isEnabled()
        assert "Folder not found" in open_btn.toolTip()
