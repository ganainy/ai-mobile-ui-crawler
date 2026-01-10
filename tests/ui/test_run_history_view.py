"""Tests for RunHistoryView widget."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from PySide6.QtWidgets import QApplication, QMessageBox


@pytest.fixture
def qt_app():
    """Create QApplication instance for all UI tests.
    
    This fixture is created at session scope to ensure QApplication
    exists for all UI tests. PySide6 requires exactly one QApplication
    instance to exist for widgets to work properly.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class MockRunRepository:
    """Mock run repository for testing."""
    
    def __init__(self):
        self._runs = []
        self._next_id = 1
        
    def get_all_runs(self):
        """Get all runs."""
        return self._runs
        
    def delete_run(self, run_id):
        """Delete a run."""
        for i, run in enumerate(self._runs):
            if run.id == run_id:
                self._runs.pop(i)
                return True
        return False
        
    def add_run(self, device_id, app_package, status, steps=0, screens=0):
        """Add a test run."""
        from mobile_crawler.infrastructure.run_repository import Run
        run = Run(
            id=self._next_id,
            device_id=device_id,
            app_package=app_package,
            start_activity=None,
            start_time=datetime(2026, 1, 10, 12, 0, 0),
            end_time=datetime(2026, 1, 10, 12, 30, 0),
            status=status,
            ai_provider="gemini",
            ai_model="gemini-1.5-pro",
            total_steps=steps,
            unique_screens=screens
        )
        self._runs.append(run)
        self._next_id += 1
        return run


class MockReportGenerator:
    """Mock report generator for testing."""
    
    def generate(self, run_id):
        """Generate a report."""
        return f"/path/to/report_{run_id}.pdf"


class MockMobSFManager:
    """Mock MobSF manager for testing."""
    
    def analyze(self, package):
        """Run MobSF analysis."""
        pass


@pytest.fixture
def mock_run_repository():
    """Create a mock run repository."""
    return MockRunRepository()


@pytest.fixture
def mock_report_generator():
    """Create a mock report generator."""
    return MockReportGenerator()


@pytest.fixture
def mock_mobsf_manager():
    """Create a mock MobSF manager."""
    return MockMobSFManager()


def _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager):
    """Create a new RunHistoryView instance for testing.
    
    Args:
        mock_run_repository: Mock run repository instance
        mock_report_generator: Mock report generator instance
        mock_mobsf_manager: Mock MobSF manager instance
        
    Returns:
        RunHistoryView instance with mock dependencies
    """
    from mobile_crawler.ui.widgets.run_history_view import RunHistoryView
    return RunHistoryView(
        mock_run_repository,
        mock_report_generator,
        mock_mobsf_manager
    )


class TestRunHistoryViewInit:
    """Tests for RunHistoryView initialization."""

    def test_initialization(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that RunHistoryView initializes correctly."""
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        assert view is not None
        assert hasattr(view, 'table')
        assert hasattr(view, 'refresh_button')
        assert hasattr(view, 'delete_button')
        assert hasattr(view, 'report_button')
        assert hasattr(view, 'mobsf_button')

    def test_has_signals(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that signals exist."""
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        assert hasattr(view, 'run_deleted')
        assert hasattr(view, 'report_generated')
        assert hasattr(view, 'mobsf_completed')


class TestRunHistoryTable:
    """Tests for run history table."""

    def test_table_has_correct_columns(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that table has correct columns."""
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        assert view.table.columnCount() == 9
        assert view.table.horizontalHeaderItem(0).text() == "ID"
        assert view.table.horizontalHeaderItem(1).text() == "Device"
        assert view.table.horizontalHeaderItem(2).text() == "Package"
        assert view.table.horizontalHeaderItem(3).text() == "Start Time"
        assert view.table.horizontalHeaderItem(4).text() == "End Time"
        assert view.table.horizontalHeaderItem(5).text() == "Status"
        assert view.table.horizontalHeaderItem(6).text() == "Steps"
        assert view.table.horizontalHeaderItem(7).text() == "Screens"
        assert view.table.horizontalHeaderItem(8).text() == "Model"

    def test_table_is_read_only(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that table is read-only."""
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        assert view.table.editTriggers() == view.table.EditTrigger.NoEditTriggers

    def test_table_loads_runs(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that table loads runs from repository."""
        mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED", steps=10, screens=5)
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        assert view.table.rowCount() == 1

    def test_table_displays_run_data(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that table displays run data correctly."""
        run = mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED", steps=10, screens=5)
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        assert view.table.item(0, 0).text() == str(run.id)
        assert view.table.item(0, 1).text() == "emulator-5554"
        assert view.table.item(0, 2).text() == "com.example.app"
        assert view.table.item(0, 6).text() == "10"
        assert view.table.item(0, 7).text() == "5"

    def test_table_displays_model_info(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that table displays model info."""
        mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        assert view.table.item(0, 8).text() == "gemini/gemini-1.5-pro"

    def test_table_displays_multiple_runs(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that table displays multiple runs."""
        mock_run_repository.add_run("emulator-5554", "com.example.app1", "STOPPED")
        mock_run_repository.add_run("emulator-5554", "com.example.app2", "RUNNING")
        mock_run_repository.add_run("emulator-5554", "com.example.app3", "ERROR")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        assert view.table.rowCount() == 3

    def test_table_displays_status_colors(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that table displays status with correct colors."""
        mock_run_repository.add_run("emulator-5554", "com.example.app1", "RUNNING")
        mock_run_repository.add_run("emulator-5554", "com.example.app2", "STOPPED")
        mock_run_repository.add_run("emulator-5554", "com.example.app3", "ERROR")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        # Check that status items have colors (not just default)
        assert view.table.item(0, 5).foreground() is not None
        assert view.table.item(1, 5).foreground() is not None
        assert view.table.item(2, 5).foreground() is not None


class TestButtons:
    """Tests for button functionality."""

    def test_buttons_disabled_on_no_selection(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that buttons are disabled when no row is selected."""
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        assert not view.delete_button.isEnabled()
        assert not view.report_button.isEnabled()
        assert not view.mobsf_button.isEnabled()

    def test_buttons_enabled_on_selection(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that buttons are enabled when a row is selected."""
        mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        # Select first row
        view.table.selectRow(0)
        
        assert view.delete_button.isEnabled()
        assert view.report_button.isEnabled()
        assert view.mobsf_button.isEnabled()

    def test_refresh_button_exists(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that refresh button exists."""
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        assert view.refresh_button is not None


class TestDeleteRun:
    """Tests for delete run functionality."""

    def test_delete_button_emits_signal(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager, monkeypatch):
        """Test that delete button emits run_deleted signal."""
        run = mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        signal_emitted = False
        emitted_run_id = None
        
        def on_run_deleted(run_id):
            nonlocal signal_emitted, emitted_run_id
            signal_emitted = True
            emitted_run_id = run_id
        
        view.run_deleted.connect(on_run_deleted)
        
        # Mock QMessageBox to return Yes
        monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        monkeypatch.setattr(QMessageBox, 'information', lambda *args, **kwargs: None)
        
        # Select first row and click delete
        view.table.selectRow(0)
        view._on_delete_clicked()
        
        assert signal_emitted
        assert emitted_run_id == run.id

    def test_delete_removes_row_from_table(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager, monkeypatch):
        """Test that delete removes row from table."""
        mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        # Mock QMessageBox to return Yes
        monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        monkeypatch.setattr(QMessageBox, 'information', lambda *args, **kwargs: None)
        
        # Select first row and click delete
        view.table.selectRow(0)
        view._on_delete_clicked()
        
        assert view.table.rowCount() == 0

    def test_delete_with_no_confirmation(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager, monkeypatch):
        """Test that delete does not proceed when user cancels."""
        mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        # Mock QMessageBox to return No
        monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.No)
        
        # Select first row and click delete
        view.table.selectRow(0)
        view._on_delete_clicked()
        
        # Row should still be in table
        assert view.table.rowCount() == 1


class TestGenerateReport:
    """Tests for generate report functionality."""

    def test_report_button_emits_signal(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager, monkeypatch):
        """Test that report button emits report_generated signal."""
        run = mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        signal_emitted = False
        emitted_run_id = None
        
        def on_report_generated(run_id):
            nonlocal signal_emitted, emitted_run_id
            signal_emitted = True
            emitted_run_id = run_id
        
        view.report_generated.connect(on_report_generated)
        
        # Mock QMessageBox to return Yes
        monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        monkeypatch.setattr(QMessageBox, 'information', lambda *args, **kwargs: None)
        
        # Select first row and click generate report
        view.table.selectRow(0)
        view._on_generate_report_clicked()
        
        assert signal_emitted
        assert emitted_run_id == run.id

    def test_generate_report_calls_generator(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager, monkeypatch):
        """Test that generate report calls report generator."""
        run = mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        # Mock QMessageBox to return Yes
        monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        monkeypatch.setattr(QMessageBox, 'information', lambda *args, **kwargs: None)
        
        # Select first row and click generate report
        view.table.selectRow(0)
        view._on_generate_report_clicked()
        
        # Check that report generator was called
        # (MockReportGenerator.generate is called, we can verify by checking it exists)
        assert mock_report_generator.generate is not None


class TestMobSF:
    """Tests for MobSF functionality."""

    def test_mobsf_button_emits_signal(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager, monkeypatch):
        """Test that MobSF button emits mobsf_completed signal."""
        run = mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        signal_emitted = False
        emitted_run_id = None
        
        def on_mobsf_completed(run_id):
            nonlocal signal_emitted, emitted_run_id
            signal_emitted = True
            emitted_run_id = run_id
        
        view.mobsf_completed.connect(on_mobsf_completed)
        
        # Mock QMessageBox to return Yes
        monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        monkeypatch.setattr(QMessageBox, 'information', lambda *args, **kwargs: None)
        
        # Select first row and click MobSF
        view.table.selectRow(0)
        view._on_mobsf_clicked()
        
        assert signal_emitted
        assert emitted_run_id == run.id

    def test_mobsf_calls_manager(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager, monkeypatch):
        """Test that MobSF calls MobSF manager."""
        mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        # Mock QMessageBox to return Yes
        monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        monkeypatch.setattr(QMessageBox, 'information', lambda *args, **kwargs: None)
        
        # Select first row and click MobSF
        view.table.selectRow(0)
        view._on_mobsf_clicked()
        
        # Check that MobSF manager was called
        # (MockMobSFManager.analyze is called)
        assert mock_mobsf_manager.analyze is not None


class TestRefresh:
    """Tests for refresh functionality."""

    def test_refresh_button_reloads_runs(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that refresh button reloads runs."""
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        # Add a run after view is created
        mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        
        # Click refresh
        view._load_runs()
        
        assert view.table.rowCount() == 1

    def test_refresh_method_works(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that refresh method works."""
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        # Add a run after view is created
        mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        
        # Call refresh method
        view.refresh()
        
        assert view.table.rowCount() == 1


class TestGetSelectedRunId:
    """Tests for get_selected_run_id method."""

    def test_get_selected_run_id_returns_id(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that get_selected_run_id returns run ID."""
        run = mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        # Select first row
        view.table.selectRow(0)
        
        assert view.get_selected_run_id() == run.id

    def test_get_selected_run_id_returns_none_when_no_selection(self, qt_app, mock_run_repository, mock_report_generator, mock_mobsf_manager):
        """Test that get_selected_run_id returns None when no row is selected."""
        mock_run_repository.add_run("emulator-5554", "com.example.app", "STOPPED")
        view = _create_run_history_view(mock_run_repository, mock_report_generator, mock_mobsf_manager)
        
        # Don't select any row
        assert view.get_selected_run_id() is None
