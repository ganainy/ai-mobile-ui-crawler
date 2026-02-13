"""Tests for delete CLI command."""

from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
import pytest

from mobile_crawler.cli.main import cli
from mobile_crawler.infrastructure.run_repository import Run


class TestDeleteCommand:
    """Test delete command."""

    def test_delete_command_help(self):
        """Test that delete command shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['delete', '--help'])
        assert result.exit_code == 0
        assert 'Delete a crawl run and all associated data' in result.output
        assert 'RUN_ID' in result.output
        assert '--yes' in result.output

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.infrastructure.run_repository.RunRepository')
    @patch('mobile_crawler.infrastructure.session_folder_manager.SessionFolderManager')
    @patch('click.confirm')
    def test_delete_with_confirmation(self, mock_confirm, mock_session_folder_manager_cls, mock_run_repo_cls, mock_db_manager_cls):
        """Test deleting a run with confirmation."""
        # Setup mocks
        mock_confirm.return_value = True
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_run = Run(
            id=1,
            device_id='emulator-5554',
            app_package='com.example.app',
            start_activity='com.example.MainActivity',
            start_time=datetime(2024, 1, 10, 12, 30),
            end_time=datetime(2024, 1, 10, 13, 30),
            status='COMPLETED',
            ai_provider='gemini',
            ai_model='gemini-1.5-flash',
            total_steps=50,
            unique_screens=15
        )
        
        mock_run_repo = Mock()
        mock_run_repo.get_run.return_value = mock_run
        mock_run_repo.delete_run.return_value = True
        mock_run_repo_cls.return_value = mock_run_repo
        
        mock_session_folder_manager = Mock()
        mock_session_folder_manager_cls.return_value = mock_session_folder_manager

        runner = CliRunner()
        result = runner.invoke(cli, ['delete', '1'])

        assert result.exit_code == 0
        assert 'Run ID: 1' in result.output
        assert 'Device: emulator-5554' in result.output
        assert 'App: com.example.app' in result.output
        assert 'Status: COMPLETED' in result.output
        assert 'Steps: 50' in result.output
        assert 'Screens: 15' in result.output
        assert 'Deleted run 1 from database' in result.output
        mock_confirm.assert_called_once()
        mock_run_repo.delete_run.assert_called_once_with(1)

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.infrastructure.run_repository.RunRepository')
    @patch('mobile_crawler.infrastructure.session_folder_manager.SessionFolderManager')
    @patch('click.confirm')
    def test_delete_with_yes_flag(self, mock_confirm, mock_session_folder_manager_cls, mock_run_repo_cls, mock_db_manager_cls):
        """Test deleting a run with --yes flag (no confirmation)."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_run = Run(
            id=1,
            device_id='emulator-5554',
            app_package='com.example.app',
            start_activity='com.example.MainActivity',
            start_time=datetime(2024, 1, 10, 12, 30),
            end_time=datetime(2024, 1, 10, 13, 30),
            status='COMPLETED',
            ai_provider='gemini',
            ai_model='gemini-1.5-flash',
            total_steps=50,
            unique_screens=15
        )
        
        mock_run_repo = Mock()
        mock_run_repo.get_run.return_value = mock_run
        mock_run_repo.delete_run.return_value = True
        mock_run_repo_cls.return_value = mock_run_repo
        
        mock_session_folder_manager = Mock()
        mock_session_folder_manager_cls.return_value = mock_session_folder_manager

        runner = CliRunner()
        result = runner.invoke(cli, ['delete', '1', '--yes'])

        assert result.exit_code == 0
        assert 'Deleted run 1 from database' in result.output
        # confirm should NOT be called with --yes flag
        mock_confirm.assert_not_called()

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.infrastructure.run_repository.RunRepository')
    @patch('mobile_crawler.infrastructure.session_folder_manager.SessionFolderManager')
    @patch('click.confirm')
    def test_delete_cancelled_by_user(self, mock_confirm, mock_session_folder_manager_cls, mock_run_repo_cls, mock_db_manager_cls):
        """Test that deletion is cancelled when user declines confirmation."""
        mock_confirm.return_value = False
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_run = Run(
            id=1,
            device_id='emulator-5554',
            app_package='com.example.app',
            start_activity='com.example.MainActivity',
            start_time=datetime(2024, 1, 10, 12, 30),
            end_time=datetime(2024, 1, 10, 13, 30),
            status='COMPLETED',
            ai_provider='gemini',
            ai_model='gemini-1.5-flash',
            total_steps=50,
            unique_screens=15
        )
        
        mock_run_repo = Mock()
        mock_run_repo.get_run.return_value = mock_run
        mock_run_repo_cls.return_value = mock_run_repo
        
        mock_session_folder_manager = Mock()
        mock_session_folder_manager_cls.return_value = mock_session_folder_manager

        runner = CliRunner()
        result = runner.invoke(cli, ['delete', '1'])

        assert result.exit_code == 0
        assert 'Deletion cancelled.' in result.output
        # delete_run should NOT be called when cancelled
        mock_run_repo.delete_run.assert_not_called()

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.infrastructure.run_repository.RunRepository')
    @patch('mobile_crawler.infrastructure.session_folder_manager.SessionFolderManager')
    def test_delete_run_not_found(self, mock_session_folder_manager_cls, mock_run_repo_cls, mock_db_manager_cls):
        """Test deleting a non-existent run."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_run_repo = Mock()
        mock_run_repo.get_run.return_value = None
        mock_run_repo_cls.return_value = mock_run_repo
        
        mock_session_folder_manager = Mock()
        mock_session_folder_manager_cls.return_value = mock_session_folder_manager

        runner = CliRunner()
        result = runner.invoke(cli, ['delete', '999', '--yes'])

        assert result.exit_code == 1
        assert 'Run not found: 999' in result.output

    def test_delete_invalid_run_id(self):
        """Test deleting with invalid run ID."""
        runner = CliRunner()
        result = runner.invoke(cli, ['delete', 'invalid', '--yes'])

        assert result.exit_code == 1
        assert 'Invalid run ID: invalid' in result.output

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.infrastructure.run_repository.RunRepository')
    @patch('mobile_crawler.infrastructure.session_folder_manager.SessionFolderManager')
    @patch('click.confirm')
    def test_delete_database_error(self, mock_confirm, mock_session_folder_manager_cls, mock_run_repo_cls, mock_db_manager_cls):
        """Test that database errors are handled."""
        mock_confirm.return_value = True
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_run = Run(
            id=1,
            device_id='emulator-5554',
            app_package='com.example.app',
            start_activity='com.example.MainActivity',
            start_time=datetime(2024, 1, 10, 12, 30),
            end_time=datetime(2024, 1, 10, 13, 30),
            status='COMPLETED',
            ai_provider='gemini',
            ai_model='gemini-1.5-flash',
            total_steps=50,
            unique_screens=15
        )
        
        mock_run_repo = Mock()
        mock_run_repo.get_run.return_value = mock_run
        mock_run_repo.delete_run.side_effect = Exception('Database connection failed')
        mock_run_repo_cls.return_value = mock_run_repo
        
        mock_session_folder_manager = Mock()
        mock_session_folder_manager_cls.return_value = mock_session_folder_manager

        runner = CliRunner()
        result = runner.invoke(cli, ['delete', '1'])

        assert result.exit_code == 1
        assert 'Error deleting run: Database connection failed' in result.output
