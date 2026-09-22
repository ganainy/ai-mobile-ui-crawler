"""Tests for the crawl CLI command."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from mobile_crawler.cli.main import cli


class TestCrawlCommand:
    """Test the crawl command."""

    def test_crawl_command_help(self):
        """Test that crawl command shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["crawl", "--help"])
        assert result.exit_code == 0
        assert "Start a crawl" in result.output
        assert "--device" in result.output
        assert "--package" in result.output
        assert "--model" in result.output

    @patch("mobile_crawler.cli.commands.crawl.DatabaseManager")
    @patch("mobile_crawler.cli.commands.crawl.ConfigManager")
    @patch("mobile_crawler.cli.commands.crawl.CrawlerLoop")
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
        with (
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as mock_run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir") as mock_get_app_data_dir,
        ):
            mock_run_repo_cls.return_value = mock_run_repo
            mock_get_app_data_dir.return_value = Mock()

            runner = CliRunner()
            result = runner.invoke(
                cli, ["crawl", "--device", "emulator-5554", "--package", "com.example.app", "--model", "gemini-pro"]
            )

            assert result.exit_code == 0
            mock_run_repo.create_run.assert_called_once()
            mock_crawler_loop.run.assert_called_once_with(123)

    @patch("mobile_crawler.cli.commands.crawl.DatabaseManager")
    @patch("mobile_crawler.cli.commands.crawl.ConfigManager")
    def test_crawl_command_with_options(self, mock_config_manager_cls, mock_db_manager_cls):
        """Test crawl command with optional parameters."""
        mock_config_manager = Mock()
        mock_config_manager.user_config_store = Mock()
        mock_config_manager_cls.return_value = mock_config_manager

        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager

        with (
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as mock_run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.CrawlerLoop") as mock_crawler_loop_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir") as mock_get_app_data_dir,
        ):
            mock_run_repo = Mock()
            mock_run_repo.create_run.return_value = 123
            mock_run_repo_cls.return_value = mock_run_repo

            mock_crawler_loop = Mock()
            mock_crawler_loop_cls.return_value = mock_crawler_loop

            mock_get_app_data_dir.return_value = Mock()

            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "crawl",
                    "--device",
                    "emulator-5554",
                    "--package",
                    "com.example.app",
                    "--model",
                    "gpt-4",
                    "--steps",
                    "50",
                    "--duration",
                    "300",
                    "--provider",
                    "openrouter",
                ],
            )

            assert result.exit_code == 0
            # Verify config overrides were set
            mock_config_manager.set.assert_any_call("max_crawl_steps", 50)
            mock_config_manager.set.assert_any_call("max_crawl_duration_seconds", 300)
            mock_config_manager.set.assert_any_call("ai_provider", "openrouter")
            mock_config_manager.set.assert_any_call("ai_model", "gpt-4")

    @patch("mobile_crawler.cli.commands.crawl.DatabaseManager")
    @patch("mobile_crawler.cli.commands.crawl.ConfigManager")
    def test_crawl_command_traffic_capture_enables_tls(self, mock_config_manager_cls, mock_db_manager_cls):
        """Traffic capture CLI flag should also request PCAPdroid TLS decryption."""
        mock_config_manager = Mock()
        mock_config_manager.user_config_store = Mock()
        mock_config_manager_cls.return_value = mock_config_manager

        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager

        with (
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as mock_run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.CrawlerLoop") as mock_crawler_loop_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir") as mock_get_app_data_dir,
        ):
            mock_run_repo = Mock()
            mock_run_repo.create_run.return_value = 123
            mock_run_repo_cls.return_value = mock_run_repo
            mock_crawler_loop_cls.return_value = Mock()
            mock_get_app_data_dir.return_value = Mock()

            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "crawl",
                    "--device",
                    "emulator-5554",
                    "--package",
                    "com.example.app",
                    "--model",
                    "gemini-pro",
                    "--enable-traffic-capture",
                ],
            )

            assert result.exit_code == 0
            mock_config_manager.set.assert_any_call("enable_traffic_capture", True)
            mock_config_manager.set.assert_any_call("pcapdroid_tls_decryption", True)


class TestCrawlRunReport:
    """The crawl command passes a report generator to the loop and can opt out of auto-reports."""

    def _run(self, extra_args):
        with (
            patch("mobile_crawler.cli.commands.crawl.DatabaseManager"),
            patch("mobile_crawler.cli.commands.crawl.ConfigManager") as config_cls,
            patch("mobile_crawler.cli.commands.crawl.ReportGenerator") as generator_cls,
            patch("mobile_crawler.cli.commands.crawl.CrawlerLoop") as loop_cls,
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir") as data_dir,
        ):
            data_dir.return_value = Mock()
            run_repo_cls.return_value.create_run.return_value = 7
            config = Mock()
            config_cls.return_value = config
            result = CliRunner().invoke(
                cli,
                [
                    "crawl",
                    "--device",
                    "emulator-5554",
                    "--package",
                    "com.example.app",
                    "--model",
                    "gemini-pro",
                    *extra_args,
                ],
            )
        return result, config, generator_cls, loop_cls

    def test_loop_receives_a_report_generator(self):
        result, _, generator_cls, loop_cls = self._run([])

        assert result.exit_code == 0
        assert loop_cls.call_args.kwargs["report_generator"] is generator_cls.return_value
        assert callable(generator_cls.call_args.kwargs["telemetry_client_factory"])

    def test_no_report_flag_turns_auto_report_off(self):
        result, config, _, _ = self._run(["--no-report"])

        assert result.exit_code == 0
        config.set.assert_any_call("auto_generate_report_after_run", False)

    def test_auto_report_is_not_overridden_by_default(self):
        _, config, _, _ = self._run([])

        assert ("auto_generate_report_after_run", False) not in [c.args for c in config.set.call_args_list]


class TestCrawlHumanFallback:
    """The crawl command wires a terminal prompter and passes through the --human-fallback override."""

    def _run(self, extra_args):
        with (
            patch("mobile_crawler.cli.commands.crawl.DatabaseManager"),
            patch("mobile_crawler.cli.commands.crawl.ConfigManager") as config_cls,
            patch("mobile_crawler.cli.commands.crawl.CrawlerLoop") as loop_cls,
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir") as data_dir,
        ):
            data_dir.return_value = Mock()
            run_repo_cls.return_value.create_run.return_value = 7
            config_cls.return_value = Mock()
            result = CliRunner().invoke(
                cli,
                [
                    "crawl",
                    "--device",
                    "emulator-5554",
                    "--package",
                    "com.example.app",
                    "--model",
                    "gemini-pro",
                    *extra_args,
                ],
            )
        return result, loop_cls

    def test_loop_always_receives_a_terminal_prompter(self):
        result, loop_cls = self._run([])

        assert result.exit_code == 0
        prompter = loop_cls.call_args.kwargs["human_prompter"]
        assert type(prompter).__name__ == "TerminalHumanPrompter"

    def test_no_override_by_default(self):
        result, loop_cls = self._run([])

        assert result.exit_code == 0
        assert loop_cls.call_args.kwargs["human_fallback_enabled_override"] is None

    def test_human_fallback_flag_overrides_to_true(self):
        result, loop_cls = self._run(["--human-fallback"])

        assert result.exit_code == 0
        assert loop_cls.call_args.kwargs["human_fallback_enabled_override"] is True

    def test_no_human_fallback_flag_overrides_to_false(self):
        result, loop_cls = self._run(["--no-human-fallback"])

        assert result.exit_code == 0
        assert loop_cls.call_args.kwargs["human_fallback_enabled_override"] is False
