"""Tests for the config CLI commands."""

import json
from unittest.mock import Mock, patch
from click.testing import CliRunner

import pytest

from mobile_crawler.cli.main import cli


class TestConfigCommands:
    """Test the config command group."""

    def test_config_command_help(self):
        """Test that config command shows help."""
        from mobile_crawler.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['config', '--help'])
        assert result.exit_code == 0
        assert 'Manage configuration settings' in result.output
        assert 'set' in result.output
        assert 'get' in result.output
        assert 'list' in result.output

    @patch('mobile_crawler.config.config_manager.ConfigManager')
    @patch('mobile_crawler.config.paths.get_app_data_dir')
    def test_config_set_regular_value(self, mock_get_app_data_dir, mock_config_manager_cls):
        """Test setting a regular configuration value."""
        mock_config_manager = Mock()
        mock_config_manager_cls.return_value = mock_config_manager
        mock_get_app_data_dir.return_value = Mock()

        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'set', 'max_steps', '100'])

        assert result.exit_code == 0
        assert 'Set config: max_steps = 100' in result.output
        mock_config_manager.set.assert_called_once_with('max_steps', 100)

    @patch('mobile_crawler.config.config_manager.ConfigManager')
    @patch('mobile_crawler.config.paths.get_app_data_dir')
    def test_config_set_secret_value(self, mock_get_app_data_dir, mock_config_manager_cls):
        """Test setting a secret value (API key)."""
        mock_config_manager = Mock()
        mock_config_manager_cls.return_value = mock_config_manager
        mock_get_app_data_dir.return_value = Mock()

        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'set', 'api_key', 'secret123'])

        assert result.exit_code == 0
        assert 'Set encrypted secret: api_key' in result.output
        mock_config_manager.user_config_store.set_secret_plaintext.assert_called_once_with('api_key', 'secret123')

    @patch('mobile_crawler.config.config_manager.ConfigManager')
    @patch('mobile_crawler.config.paths.get_app_data_dir')
    def test_config_get_regular_value(self, mock_get_app_data_dir, mock_config_manager_cls):
        """Test getting a regular configuration value."""
        mock_config_manager = Mock()
        mock_config_manager.get.return_value = 'test_value'
        mock_config_manager.user_config_store = Mock()
        mock_config_manager_cls.return_value = mock_config_manager
        mock_get_app_data_dir.return_value = Mock()

        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'get', 'test_key_123'])

        assert result.exit_code == 0
        assert 'test_value' in result.output
        mock_config_manager.get.assert_called_once_with('test_key_123')

    @patch('mobile_crawler.config.config_manager.ConfigManager')
    def test_config_get_secret_value(self, mock_config_manager_cls):
        """Test getting a secret value."""
        mock_config_manager = Mock()
        mock_config_manager.get.return_value = None
        mock_config_manager.user_config_store.get_secret_plaintext.return_value = 'decrypted_secret'
        mock_config_manager_cls.return_value = mock_config_manager

        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'get', 'api_key'])

        assert result.exit_code == 0
        assert '[ENCRYPTED] decrypted_secret' in result.output

    @patch('mobile_crawler.config.config_manager.ConfigManager')
    def test_config_get_not_found(self, mock_config_manager_cls):
        """Test getting a non-existent configuration value."""
        mock_config_manager = Mock()
        mock_config_manager.get.return_value = None
        mock_config_manager.user_config_store.get_secret_plaintext.return_value = None
        mock_config_manager_cls.return_value = mock_config_manager

        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'get', 'nonexistent'])

        assert result.exit_code == 1
        assert 'Config key not found: nonexistent' in result.output

    @patch('mobile_crawler.config.config_manager.ConfigManager')
    @patch('mobile_crawler.config.paths.get_app_data_dir')
    def test_config_list_with_settings(self, mock_get_app_data_dir, mock_config_manager_cls):
        """Test listing configuration settings."""
        mock_config_manager = Mock()
        mock_config_manager.user_config_store = Mock()
        mock_config_manager.user_config_store.get_all_settings.return_value = {
            'max_steps': 100,
            'timeout': 30.5,
            'debug': True,
            'model': 'gpt-4'
        }

        # Mock the secrets query
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [{'key': 'api_key'}, {'key': 'token'}]
        mock_conn.cursor.return_value = mock_cursor
        mock_config_manager.user_config_store.get_connection.return_value = mock_conn

        mock_config_manager_cls.return_value = mock_config_manager
        mock_get_app_data_dir.return_value = Mock()

        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'list'])

        assert result.exit_code == 0
        assert 'Configuration Settings:' in result.output
        assert 'max_steps: 100' in result.output
        assert 'timeout: 30.5' in result.output
        assert 'debug: True' in result.output
        assert 'model: gpt-4' in result.output
        assert 'Encrypted Secrets:' in result.output
        assert 'api_key: [ENCRYPTED]' in result.output
        assert 'token: [ENCRYPTED]' in result.output

    @patch('mobile_crawler.config.config_manager.ConfigManager')
    def test_config_list_empty(self, mock_config_manager_cls):
        """Test listing when no configuration exists."""
        mock_config_manager = Mock()
        mock_config_manager.user_config_store.get_all_settings.return_value = {}

        # Mock empty secrets
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_config_manager.user_config_store.get_connection.return_value = mock_conn

        mock_config_manager_cls.return_value = mock_config_manager

        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'list'])

        assert result.exit_code == 0
        assert 'No configuration settings found.' in result.output