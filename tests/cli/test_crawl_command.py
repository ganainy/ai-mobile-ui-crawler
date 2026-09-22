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


class TestCrawlDockerAutostart:
    """The crawl command auto-starts MobSF/OmniParser Docker containers before crawling."""

    def _run(self, extra_args, mobsf_result=None, omniparser_result=None):
        with (
            patch("mobile_crawler.cli.commands.crawl.DatabaseManager"),
            patch("mobile_crawler.cli.commands.crawl.ConfigManager") as config_cls,
            patch("mobile_crawler.cli.commands.crawl.CrawlerLoop"),
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir") as data_dir,
            patch(
                "mobile_crawler.cli.commands.crawl.ensure_mobsf_running_if_enabled",
                return_value=mobsf_result,
            ) as ensure_mobsf,
            patch(
                "mobile_crawler.cli.commands.crawl.ensure_omniparser_running_if_enabled",
                return_value=omniparser_result,
            ) as ensure_omniparser,
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
        return result, ensure_mobsf, ensure_omniparser

    def test_docker_autostart_is_attempted_before_crawl(self):
        result, ensure_mobsf, ensure_omniparser = self._run([])

        assert result.exit_code == 0
        ensure_mobsf.assert_called_once()
        ensure_omniparser.assert_called_once()

    def test_successful_start_is_reported_on_stderr_not_stdout(self):
        result, _, _ = self._run([], mobsf_result=(True, "MobSF is ready"))

        assert result.exit_code == 0
        assert "MobSF: MobSF is ready" in result.stderr
        assert "MobSF: MobSF is ready" not in result.stdout

    def test_failed_start_is_a_warning_not_a_failure(self):
        result, _, _ = self._run([], mobsf_result=(False, "Docker is not available"))

        assert result.exit_code == 0
        assert "Docker is not available" in result.stderr
        assert "Docker is not available" not in result.stdout

    def test_skipped_autostart_reports_nothing(self):
        result, _, _ = self._run([], mobsf_result=None, omniparser_result=None)

        assert result.exit_code == 0
        assert "MobSF" not in result.output
        assert "OmniParser" not in result.output


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


class TestCrawlStepByStep:
    """--step-by-step turns on the loop's step-by-step mode and adds the terminal pause console."""

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

    def test_step_by_step_is_off_by_default(self):
        result, loop_cls = self._run([])

        assert result.exit_code == 0
        loop = loop_cls.return_value
        loop.set_step_by_step_enabled.assert_not_called()
        loop.add_event_listener.assert_not_called()

    def test_flag_enables_step_by_step_before_the_run(self):
        result, loop_cls = self._run(["--step-by-step"])

        assert result.exit_code == 0
        loop = loop_cls.return_value
        loop.set_step_by_step_enabled.assert_called_once_with(True)
        call_names = [c[0] for c in loop.method_calls]
        assert call_names.index("set_step_by_step_enabled") < call_names.index("run")

    def test_flag_adds_a_console_that_advances_the_loop(self):
        result, loop_cls = self._run(["--step-by-step"])

        assert result.exit_code == 0
        loop = loop_cls.return_value
        consoles = [c.args[0] for c in loop.add_event_listener.call_args_list]
        assert len(consoles) == 1 and type(consoles[0]).__name__ == "StepByStepConsole"
        consoles[0]._advance()
        loop.advance_step.assert_called_once_with()

    def test_console_shares_the_human_prompters_stdin_reader(self):
        result, loop_cls = self._run(["--step-by-step"])

        assert result.exit_code == 0
        prompter = loop_cls.call_args.kwargs["human_prompter"]
        console = loop_cls.return_value.add_event_listener.call_args.args[0]
        assert console._reader is prompter._reader
