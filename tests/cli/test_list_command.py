"""Tests for list CLI command."""

from datetime import datetime
from unittest.mock import Mock, patch
from click.testing import CliRunner

import pytest

from mobile_crawler.cli.main import cli
from mobile_crawler.infrastructure.run_repository import Run
from mobile_crawler.infrastructure.device_detection import AndroidDevice


class TestListCommand:
    """Test list command."""

    def test_list_command_help(self):
        """Test that list command shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--help'])
        assert result.exit_code == 0
        assert 'List runs or devices' in result.output
        assert 'TARGET' in result.output
        assert '--limit' in result.output
        assert '--format' in result.output

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.infrastructure.run_repository.RunRepository')
    def test_list_runs_table_format(self, mock_run_repo_cls, mock_db_manager_cls):
        """Test listing runs in table format."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_run_repo = Mock()
        mock_run1 = Mock()
        mock_run1.id = 1
        mock_run1.device_id = 'emulator-5554'
        mock_run1.app_package = 'com.example.app'
        mock_run1.start_time = datetime(2024, 1, 10, 12, 30)
        mock_run1.status = 'COMPLETED'
        mock_run1.total_steps = 50
        mock_run1.unique_screens = 15
        
        mock_run2 = Mock()
        mock_run2.id = 2
        mock_run2.device_id = 'emulator-5554'
        mock_run2.app_package = 'com.test.app'
        mock_run2.start_time = datetime(2024, 1, 10, 14, 45)
        mock_run2.status = 'STOPPED'
        mock_run2.total_steps = 25
        mock_run2.unique_screens = 8
        
        mock_run_repo.get_recent_runs.return_value = [mock_run1, mock_run2]
        mock_run_repo_cls.return_value = mock_run_repo

        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'runs'])

        assert result.exit_code == 0
        assert 'Recent Runs:' in result.output
        assert '1' in result.output
        assert 'emulator-5554' in result.output
        assert 'com.example.app' in result.output
        assert 'COMPLETED' in result.output
        mock_run_repo.get_recent_runs.assert_called_once_with(10)

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.infrastructure.run_repository.RunRepository')
    def test_list_runs_json_format(self, mock_run_repo_cls, mock_db_manager_cls):
        """Test listing runs in JSON format."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_run_repo = Mock()
        mock_run = Mock()
        mock_run.id = 1
        mock_run.device_id = 'emulator-5554'
        mock_run.app_package = 'com.example.app'
        mock_run.start_time = datetime(2024, 1, 10, 12, 30)
        mock_run.status = 'COMPLETED'
        mock_run.total_steps = 50
        mock_run.unique_screens = 15
        
        mock_run_repo.get_recent_runs.return_value = [mock_run]
        mock_run_repo_cls.return_value = mock_run_repo

        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'runs', '--format', 'json'])

        assert result.exit_code == 0
        assert '"id": 1' in result.output
        assert '"device_id": "emulator-5554"' in result.output
        assert '"app_package": "com.example.app"' in result.output
        assert '"status": "COMPLETED"' in result.output

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.infrastructure.run_repository.RunRepository')
    def test_list_runs_empty(self, mock_run_repo_cls, mock_db_manager_cls):
        """Test listing runs when no runs exist."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_run_repo = Mock()
        mock_run_repo.get_recent_runs.return_value = []
        mock_run_repo_cls.return_value = mock_run_repo

        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'runs'])

        assert result.exit_code == 0
        assert 'No runs found.' in result.output

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.infrastructure.run_repository.RunRepository')
    def test_list_runs_with_limit(self, mock_run_repo_cls, mock_db_manager_cls):
        """Test listing runs with custom limit."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_run_repo = Mock()
        mock_run = Mock()
        mock_run.id = 1
        mock_run.device_id = 'emulator-5554'
        mock_run.app_package = 'com.example.app'
        mock_run.start_time = datetime(2024, 1, 10, 12, 30)
        mock_run.status = 'COMPLETED'
        mock_run.total_steps = 50
        mock_run.unique_screens = 15
        
        mock_run_repo.get_recent_runs.return_value = [mock_run]
        mock_run_repo_cls.return_value = mock_run_repo

        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'runs', '--limit', '5'])

        assert result.exit_code == 0
        mock_run_repo.get_recent_runs.assert_called_once_with(5)

    @patch('mobile_crawler.infrastructure.device_detection.DeviceDetection')
    def test_list_devices_table_format(self, mock_device_detection_cls):
        """Test listing devices in table format."""
        mock_device_detection = Mock()
        mock_device1 = Mock()
        mock_device1.device_id = 'emulator-5554'
        mock_device1.model = 'Pixel 4 API 30'
        mock_device1.android_version = '11.0'
        mock_device1.status = 'device'
        
        mock_device2 = Mock()
        mock_device2.device_id = 'emulator-5556'
        mock_device2.model = 'Pixel 5 API 31'
        mock_device2.android_version = '12.0'
        mock_device2.status = 'device'
        
        mock_device_detection.get_connected_devices.return_value = [mock_device1, mock_device2]
        mock_device_detection_cls.return_value = mock_device_detection

        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'devices'])

        assert result.exit_code == 0
        assert 'Connected Devices:' in result.output
        assert 'emulator-5554' in result.output
        assert 'Pixel 4 API 30' in result.output
        assert 'Android' in result.output
        mock_device_detection.get_connected_devices.assert_called_once()

    @patch('mobile_crawler.infrastructure.device_detection.DeviceDetection')
    def test_list_devices_json_format(self, mock_device_detection_cls):
        """Test listing devices in JSON format."""
        mock_device_detection = Mock()
        mock_device = Mock()
        mock_device.device_id = 'emulator-5554'
        mock_device.model = 'Pixel 4 API 30'
        mock_device.android_version = '11.0'
        mock_device.status = 'device'
        
        mock_device_detection.get_connected_devices.return_value = [mock_device]
        mock_device_detection_cls.return_value = mock_device_detection

        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'devices', '--format', 'json'])

        assert result.exit_code == 0
        assert '"id": "emulator-5554"' in result.output
        assert '"name": "Pixel 4 API 30"' in result.output
        assert '"platform": "Android"' in result.output
        assert '"version": "11.0"' in result.output

    @patch('mobile_crawler.infrastructure.device_detection.DeviceDetection')
    def test_list_devices_empty(self, mock_device_detection_cls):
        """Test listing devices when no devices are connected."""
        mock_device_detection = Mock()
        mock_device_detection.get_connected_devices.return_value = []
        mock_device_detection_cls.return_value = mock_device_detection

        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'devices'])

        assert result.exit_code == 0
        assert 'No devices found.' in result.output

    @patch('mobile_crawler.infrastructure.device_detection.DeviceDetection')
    def test_list_devices_with_limit(self, mock_device_detection_cls):
        """Test listing devices with custom limit."""
        mock_device_detection = Mock()
        mock_device1 = Mock()
        mock_device1.device_id = 'emulator-5554'
        mock_device1.model = 'Pixel 4 API 30'
        mock_device1.android_version = '11.0'
        mock_device1.status = 'device'
        
        mock_device2 = Mock()
        mock_device2.device_id = 'emulator-5556'
        mock_device2.model = 'Pixel 5 API 31'
        mock_device2.android_version = '12.0'
        mock_device2.status = 'device'
        
        mock_device_detection.get_connected_devices.return_value = [mock_device1, mock_device2]
        mock_device_detection_cls.return_value = mock_device_detection

        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'devices', '--limit', '1'])

        assert result.exit_code == 0
        # Only first device should be shown
        assert 'emulator-5554' in result.output
        assert 'emulator-5556' not in result.output

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.infrastructure.run_repository.RunRepository')
    def test_list_runs_error(self, mock_run_repo_cls, mock_db_manager_cls):
        """Test that list runs errors are handled."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_run_repo = Mock()
        mock_run_repo.get_recent_runs.side_effect = Exception('Database connection failed')
        mock_run_repo_cls.return_value = mock_run_repo

        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'runs'])

        assert result.exit_code == 1
        assert 'Error listing runs: Database connection failed' in result.output

    @patch('mobile_crawler.infrastructure.device_detection.DeviceDetection')
    def test_list_devices_error(self, mock_device_detection_cls):
        """Test that list devices errors are handled."""
        mock_device_detection = Mock()
        mock_device_detection.get_connected_devices.side_effect = Exception('ADB not found')
        mock_device_detection_cls.return_value = mock_device_detection

        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'devices'])

        assert result.exit_code == 1
        assert 'Error listing devices: ADB not found' in result.output

    def test_list_invalid_target(self):
        """Test that invalid target is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'invalid'])

        assert result.exit_code == 2
        assert 'Invalid value for' in result.output or 'Invalid choice' in result.output
