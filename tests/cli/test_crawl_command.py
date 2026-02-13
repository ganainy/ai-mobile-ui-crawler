"""Tests for the crawl CLI command."""

import json
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner

from mobile_crawler.cli.main import cli


class TestCrawlCommand:
    """Test the crawl command."""

    def test_crawl_command_help(self):
        """Test that crawl command shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['crawl', '--help'])
        assert result.exit_code == 0
        assert 'Start a crawl' in result.output
        assert '--device' in result.output
        assert '--package' in result.output
        assert '--model' in result.output

    @patch('mobile_crawler.cli.commands.crawl.DatabaseManager')
    @patch('mobile_crawler.cli.commands.crawl.ConfigManager')
    @patch('mobile_crawler.cli.commands.crawl.CrawlerLoop')
    def test_crawl_command_basic(self, mock_crawler_loop_cls, mock_config_manager_cls, mock_db_manager_cls):
        """Test basic crawl command execution."""
        # Setup mocks
        mock_config_manager = Mock()
        mock_config_manager.user_config_store = Mock()
        mock_config_manager_cls.return_value = mock_config_manager

        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager

        mock_run_repo = Mock()
        mock_run_repo.create_run.return_value = 123

        mock_crawler_loop = Mock()
        mock_crawler_loop_cls.return_value = mock_crawler_loop

        # Mock the RunRepository
        with patch('mobile_crawler.cli.commands.crawl.RunRepository') as mock_run_repo_cls:
            mock_run_repo_cls.return_value = mock_run_repo

            # Mock other dependencies
            with patch('mobile_crawler.cli.commands.crawl.CrawlStateMachine') as mock_state_machine_cls, \
                 patch('mobile_crawler.cli.commands.crawl.ScreenshotCapture') as mock_screenshot_cls, \
                 patch('mobile_crawler.cli.commands.crawl.AIInteractionService') as mock_ai_cls, \
                 patch('mobile_crawler.cli.commands.crawl.ActionExecutor') as mock_action_cls, \
                 patch('mobile_crawler.cli.commands.crawl.StepLogRepository') as mock_step_log_cls, \
                 patch('mobile_crawler.cli.commands.crawl.get_app_data_dir') as mock_get_app_data_dir:

                # Configure mocks to return Mock instances when called
                mock_state_machine_cls.return_value = Mock()
                mock_screenshot_cls.side_effect = lambda *args, **kwargs: Mock()
                mock_ai_cls.return_value = Mock()
                mock_action_cls.return_value = Mock()
                mock_step_log_cls.return_value = Mock()
                mock_get_app_data_dir.return_value = Mock()

                runner = CliRunner()
                result = runner.invoke(cli, [
                    'crawl',
                    '--device', 'emulator-5554',
                    '--package', 'com.example.app',
                    '--model', 'gemini-pro'
                ])

                assert result.exit_code == 0
                mock_run_repo.create_run.assert_called_once()
                mock_crawler_loop.run.assert_called_once_with(123)

    @patch('mobile_crawler.cli.commands.crawl.DatabaseManager')
    @patch('mobile_crawler.cli.commands.crawl.ConfigManager')
    def test_crawl_command_with_options(self, mock_config_manager_cls, mock_db_manager_cls):
        """Test crawl command with optional parameters."""
        mock_config_manager = Mock()
        mock_config_manager.user_config_store = Mock()
        mock_config_manager_cls.return_value = mock_config_manager

        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager

        with patch('mobile_crawler.cli.commands.crawl.RunRepository') as mock_run_repo_cls, \
             patch('mobile_crawler.cli.commands.crawl.CrawlerLoop') as mock_crawler_loop_cls, \
             patch('mobile_crawler.cli.commands.crawl.CrawlStateMachine') as mock_state_machine_cls, \
             patch('mobile_crawler.cli.commands.crawl.ScreenshotCapture') as mock_screenshot_cls, \
             patch('mobile_crawler.cli.commands.crawl.AIInteractionService') as mock_ai_cls, \
             patch('mobile_crawler.cli.commands.crawl.ActionExecutor') as mock_action_cls, \
             patch('mobile_crawler.cli.commands.crawl.StepLogRepository') as mock_step_log_cls, \
             patch('mobile_crawler.cli.commands.crawl.get_app_data_dir') as mock_get_app_data_dir:

            mock_run_repo = Mock()
            mock_run_repo.create_run.return_value = 123
            mock_run_repo_cls.return_value = mock_run_repo

            mock_crawler_loop = Mock()
            mock_crawler_loop_cls.return_value = mock_crawler_loop

            # Configure mocks
            mock_state_machine_cls.return_value = Mock()
            mock_screenshot_cls.side_effect = lambda *args, **kwargs: Mock()
            mock_ai_cls.return_value = Mock()
            mock_action_cls.return_value = Mock()
            mock_step_log_cls.return_value = Mock()
            mock_get_app_data_dir.return_value = Mock()

            runner = CliRunner()
            result = runner.invoke(cli, [
                'crawl',
                '--device', 'emulator-5554',
                '--package', 'com.example.app',
                '--model', 'gpt-4',
                '--steps', '50',
                '--duration', '300',
                '--provider', 'openrouter'
            ])

            assert result.exit_code == 0
            # Verify config overrides were set
            mock_config_manager.set.assert_any_call('max_crawl_steps', 50)
            mock_config_manager.set.assert_any_call('max_crawl_duration_seconds', 300)
            mock_config_manager.set.assert_any_call('ai_provider', 'openrouter')
            mock_config_manager.set.assert_any_call('ai_model', 'gpt-4')