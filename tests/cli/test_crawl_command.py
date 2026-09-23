"""Tests for the crawl CLI command."""

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from mobile_crawler.cli.main import cli


@pytest.fixture(autouse=True)
def no_pre_run_warnings():
    """The real checks talk to adb and the network."""
    with patch("mobile_crawler.cli.commands.crawl.collect_pre_run_warnings", return_value=[]) as collect:
        yield collect


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
                    "--duration",
                    "300",
                    "--provider",
                    "openrouter",
                ],
            )

            assert result.exit_code == 0
            # Single-run overrides, never written to the settings store
            mock_config_manager.override.assert_any_call("limit_type", "duration")
            mock_config_manager.override.assert_any_call("max_duration_seconds", 300)
            mock_config_manager.override.assert_any_call("ai_provider", "openrouter")
            mock_config_manager.override.assert_any_call("ai_model", "gpt-4")
            mock_config_manager.set.assert_not_called()

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
            mock_config_manager.override.assert_any_call("enable_traffic_capture", True)
            mock_config_manager.override.assert_any_call("pcapdroid_tls_decryption", True)


class TestCrawlDockerAutostart:
    """The crawl command auto-starts the MobSF/OmniParser/Phoenix Docker containers before crawling."""

    def _run(self, extra_args, mobsf_result=None, omniparser_result=None, phoenix_result=None):
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
            patch(
                "mobile_crawler.cli.commands.crawl.ensure_phoenix_running_if_enabled",
                return_value=phoenix_result,
            ) as ensure_phoenix,
        ):
            self.ensure_phoenix = ensure_phoenix
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
        self.ensure_phoenix.assert_called_once()

    def test_phoenix_start_is_reported_on_stderr(self):
        result, _, _ = self._run([], phoenix_result=(True, "Phoenix is ready"))

        assert result.exit_code == 0
        assert "Phoenix: Phoenix is ready" in result.stderr
        assert "Phoenix" not in result.stdout

    def test_phoenix_start_failure_is_left_to_the_pre_run_warning(self):
        # The Pre-run Warning already names the failure; don't print it twice.
        result, _, _ = self._run([], phoenix_result=(False, "Docker is not available"))

        assert result.exit_code == 0
        assert "Phoenix could not be started automatically" not in result.stderr

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
        assert "Phoenix" not in result.output


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
        config.override.assert_any_call("auto_generate_report_after_run", False)
        config.set.assert_not_called()

    def test_auto_report_is_not_overridden_by_default(self):
        _, config, _, _ = self._run([])

        assert ("auto_generate_report_after_run", False) not in [c.args for c in config.override.call_args_list]


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


class TestCrawlRunOverrides:
    """--parser-mode, --reasoning-mode and --exploration-objective override config for this run only."""

    def _run(self, extra_args):
        # Config calls made before OmniParser auto-start, for the ordering test.
        self.calls_before_omniparser = []
        with (
            patch("mobile_crawler.cli.commands.crawl.DatabaseManager"),
            patch("mobile_crawler.cli.commands.crawl.ConfigManager") as config_cls,
            patch("mobile_crawler.cli.commands.crawl.CrawlerLoop"),
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir") as data_dir,
            patch("mobile_crawler.cli.commands.crawl.ensure_mobsf_running_if_enabled", return_value=None),
            patch("mobile_crawler.cli.commands.crawl.ensure_omniparser_running_if_enabled") as omniparser,
        ):
            data_dir.return_value = Mock()
            run_repo_cls.return_value.create_run.return_value = 7
            config = Mock()
            config.get.return_value = None
            config_cls.return_value = config
            omniparser.side_effect = lambda cm: self.calls_before_omniparser.extend(cm.method_calls)
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
        return result, config

    @staticmethod
    def _keys(calls):
        return {c.args[0] for c in calls}

    def _run_override_keys(self, config):
        # --model is required, and every run sets its app package; neither is a per-flag override.
        return self._keys(c for c in config.override.call_args_list if c.args[0] not in ("ai_model", "app_package"))

    def test_no_overrides_by_default(self):
        result, config = self._run([])

        assert result.exit_code == 0
        assert self._run_override_keys(config) == set()

    def test_parser_mode_overrides_without_persisting(self):
        result, config = self._run(["--parser-mode", "accessibility"])

        assert result.exit_code == 0
        config.override.assert_any_call("ui_parser_mode", "accessibility")
        assert self._run_override_keys(config) == {"ui_parser_mode"}
        assert "ui_parser_mode" not in self._keys(config.set.call_args_list)

    def test_restart_app_flag_overrides_to_true(self):
        result, config = self._run(["--restart-app"])

        assert result.exit_code == 0
        config.override.assert_any_call("restart_app_before_run", True)

    def test_no_restart_app_flag_overrides_without_persisting(self):
        result, config = self._run(["--no-restart-app"])

        assert result.exit_code == 0
        config.override.assert_any_call("restart_app_before_run", False)
        assert "restart_app_before_run" not in self._keys(config.set.call_args_list)

    def test_parser_mode_rejects_unknown_values(self):
        result, config = self._run(["--parser-mode", "ocr"])

        assert result.exit_code == 2
        assert "--parser-mode" in result.output
        config.override.assert_not_called()

    def test_parser_mode_override_applies_before_docker_autostart(self):
        # OmniParser auto-start reads ui_parser_mode, so the override must already be in place.
        result, _ = self._run(["--parser-mode", "accessibility"])

        assert result.exit_code == 0
        assert "override" in [c[0] for c in self.calls_before_omniparser]

    def test_reasoning_mode_flag_overrides_to_true(self):
        result, config = self._run(["--reasoning-mode"])

        assert result.exit_code == 0
        config.override.assert_any_call("crawler_reasoning_mode", True)

    def test_no_reasoning_mode_flag_overrides_to_false(self):
        result, config = self._run(["--no-reasoning-mode"])

        assert result.exit_code == 0
        config.override.assert_any_call("crawler_reasoning_mode", False)
        assert "crawler_reasoning_mode" not in self._keys(config.set.call_args_list)

    def test_exploration_objective_overrides_without_persisting(self):
        result, config = self._run(["--exploration-objective", "Find the settings screen"])

        assert result.exit_code == 0
        config.override.assert_any_call("exploration_objective", "Find the settings screen")
        assert "exploration_objective" not in self._keys(config.set.call_args_list)


class TestCrawlLastDeviceAndPackage:
    """--device last / --package last resolve to the persisted last-used device and app."""

    def _run(self, device, package, saved):
        with (
            patch("mobile_crawler.cli.commands.crawl.DatabaseManager"),
            patch("mobile_crawler.cli.commands.crawl.ConfigManager") as config_cls,
            patch("mobile_crawler.cli.commands.crawl.CrawlerLoop") as loop_cls,
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir") as data_dir,
        ):
            data_dir.return_value = Mock()
            run_repo_cls.return_value.create_run.return_value = 7
            config = Mock()
            config.user_config_store.get_setting.side_effect = lambda key, default=None: saved.get(key, default)
            config_cls.return_value = config
            result = CliRunner().invoke(
                cli, ["crawl", "--device", device, "--package", package, "--model", "gemini-pro"]
            )
        return result, config, run_repo_cls.return_value, loop_cls

    def test_device_last_uses_the_saved_device(self):
        result, _, run_repo, _ = self._run("last", "com.example.app", {"last_device_id": "R5CT1234"})

        assert result.exit_code == 0
        assert run_repo.create_run.call_args.args[0].device_id == "R5CT1234"

    def test_package_last_uses_the_saved_package(self):
        result, config, run_repo, _ = self._run("emulator-5554", "last", {"last_app_package": "com.saved.app"})

        assert result.exit_code == 0
        assert run_repo.create_run.call_args.args[0].app_package == "com.saved.app"
        config.override.assert_any_call("app_package", "com.saved.app")

    def test_both_last_resolve_together(self):
        saved = {"last_device_id": "R5CT1234", "last_app_package": "com.saved.app"}
        result, _, run_repo, _ = self._run("last", "last", saved)

        assert result.exit_code == 0
        run = run_repo.create_run.call_args.args[0]
        assert (run.device_id, run.app_package) == ("R5CT1234", "com.saved.app")

    def test_explicit_values_do_not_read_saved_settings(self):
        saved = {"last_device_id": "R5CT1234", "last_app_package": "com.saved.app"}
        result, config, run_repo, _ = self._run("emulator-5554", "com.example.app", saved)

        assert result.exit_code == 0
        run = run_repo.create_run.call_args.args[0]
        assert (run.device_id, run.app_package) == ("emulator-5554", "com.example.app")
        read_keys = [c.args[0] for c in config.user_config_store.get_setting.call_args_list]
        assert "last_device_id" not in read_keys and "last_app_package" not in read_keys

    def test_device_last_without_saved_device_fails_before_the_run(self):
        result, _, run_repo, loop_cls = self._run("last", "com.example.app", {})

        assert result.exit_code == 1
        assert "last_device_id" in result.stderr
        run_repo.create_run.assert_not_called()
        loop_cls.assert_not_called()

    def test_package_last_without_saved_package_fails_before_the_run(self):
        result, _, run_repo, loop_cls = self._run("emulator-5554", "last", {})

        assert result.exit_code == 1
        assert "last_app_package" in result.stderr
        run_repo.create_run.assert_not_called()
        loop_cls.assert_not_called()

    def test_help_mentions_last(self):
        result = CliRunner().invoke(cli, ["crawl", "--help"])

        assert result.exit_code == 0
        assert "'last'" in result.output


class TestCrawlPreRunWarnings:
    """Pre-run warnings (Portal off, Phoenix down) are printed to stderr before the run starts."""

    def _run(self):
        with (
            patch("mobile_crawler.cli.commands.crawl.DatabaseManager"),
            patch("mobile_crawler.cli.commands.crawl.ConfigManager") as config_cls,
            patch("mobile_crawler.cli.commands.crawl.CrawlerLoop") as loop_cls,
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir") as data_dir,
            patch("mobile_crawler.cli.commands.crawl.ensure_mobsf_running_if_enabled", return_value=None),
            patch("mobile_crawler.cli.commands.crawl.ensure_omniparser_running_if_enabled", return_value=None),
        ):
            data_dir.return_value = Mock()
            run_repo_cls.return_value.create_run.return_value = 7
            config_cls.return_value.get.return_value = None
            result = CliRunner().invoke(
                cli,
                ["crawl", "--device", "emulator-5554", "--package", "com.example.app", "--model", "gemini-pro"],
            )
        return result, loop_cls

    def test_warnings_go_to_stderr_and_the_run_still_starts(self, no_pre_run_warnings):
        no_pre_run_warnings.return_value = ["Portal is off", "Phoenix is down"]

        result, loop_cls = self._run()

        assert result.exit_code == 0
        assert "Warning: Portal is off" in result.stderr
        assert "Warning: Phoenix is down" in result.stderr
        assert "Warning" not in result.stdout
        loop_cls.return_value.run.assert_called_once_with(7)
        assert no_pre_run_warnings.call_args.args[1] == "emulator-5554"

    def test_crawler_loop_gets_a_run_stats_repository(self):
        result, loop_cls = self._run()

        assert result.exit_code == 0
        assert loop_cls.call_args.kwargs["run_stats_repository"] is not None


class TestCrawlPreRunWarnings:
    """Pre-run warnings go to stderr, with the portal command as the fix for Portal problems."""

    def test_portal_warning_prints_the_enable_command(self, no_pre_run_warnings):
        from mobile_crawler.core.pre_run_warnings import PreRunWarning

        no_pre_run_warnings.return_value = [
            PreRunWarning("Portal is installed but its accessibility service is off", portal_fix="enable"),
            PreRunWarning("Phoenix is down"),
        ]
        with (
            patch("mobile_crawler.cli.commands.crawl.DatabaseManager"),
            patch("mobile_crawler.cli.commands.crawl.ConfigManager") as config_cls,
            patch("mobile_crawler.cli.commands.crawl.CrawlerLoop"),
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir"),
            patch("mobile_crawler.cli.commands.crawl.ensure_mobsf_running_if_enabled", return_value=None),
            patch("mobile_crawler.cli.commands.crawl.ensure_omniparser_running_if_enabled", return_value=None),
        ):
            run_repo_cls.return_value.create_run.return_value = 7
            config_cls.return_value.get.return_value = None
            result = CliRunner().invoke(
                cli, ["crawl", "--device", "dev-1", "--package", "com.example.app", "--model", "m"]
            )

        assert "Warning: Portal is installed but its accessibility service is off" in result.stderr
        assert "Fix: mobile-crawler-cli a11y-portal enable --device dev-1" in result.stderr
        assert result.stderr.count("Fix:") == 1
        assert "Warning: Phoenix is down" in result.stderr



class TestCrawlLimits:
    """--steps / --duration pick the limit type for this run and are never saved to settings."""

    def _run(self, extra_args):
        with (
            patch("mobile_crawler.cli.commands.crawl.DatabaseManager"),
            patch("mobile_crawler.cli.commands.crawl.ConfigManager") as config_cls,
            patch("mobile_crawler.cli.commands.crawl.CrawlerLoop"),
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir") as data_dir,
        ):
            data_dir.return_value = Mock()
            run_repo_cls.return_value.create_run.return_value = 7
            config = Mock()
            config_cls.return_value = config
            result = CliRunner().invoke(
                cli,
                ["crawl", "--device", "emulator-5554", "--package", "com.example.app", "--model", "m", *extra_args],
            )
        return result, config

    def test_duration_switches_the_limit_to_duration(self):
        result, config = self._run(["--duration", "600"])

        assert result.exit_code == 0
        config.override.assert_any_call("limit_type", "duration")
        config.override.assert_any_call("max_duration_seconds", 600)
        config.set.assert_not_called()

    def test_steps_switches_the_limit_to_steps(self):
        result, config = self._run(["--steps", "40"])

        assert result.exit_code == 0
        config.override.assert_any_call("limit_type", "steps")
        config.override.assert_any_call("max_steps", 40)
        config.set.assert_not_called()

    def test_steps_and_duration_together_are_rejected(self):
        result, config = self._run(["--steps", "40", "--duration", "600"])

        assert result.exit_code == 2
        assert "mutually exclusive" in result.output
        config.override.assert_not_called()

    def test_feature_flags_are_not_saved_to_settings(self):
        result, config = self._run(
            ["--provider", "gemini", "--enable-video-recording", "--enable-mobsf-analysis", "--no-report"]
        )

        assert result.exit_code == 0
        for key in ("ai_provider", "enable_video_recording", "enable_mobsf_analysis", "auto_run_mobsf_after_crawl"):
            assert key in {c.args[0] for c in config.override.call_args_list}
        config.set.assert_not_called()


class TestCrawlBatch:
    """Several --package values crawl one app after another, each as its own run."""

    def _run(self, packages, extra_args=(), installed=None, statuses=None, fallback_setting=False):
        installed = installed if installed is not None else set(packages)
        statuses = statuses or {}
        created = []

        def create_run(run):
            created.append(run)
            return 100 + len(created)

        def get_run_by_id(run_id):
            package = created[run_id - 101].app_package
            status, reason = statuses.get(package, ("COMPLETED", "duration_limit"))
            return Mock(status=status, stop_reason=reason, total_steps=3, unique_screens=2)

        with (
            patch("mobile_crawler.cli.commands.crawl.DatabaseManager"),
            patch("mobile_crawler.cli.commands.crawl.ConfigManager") as config_cls,
            patch("mobile_crawler.cli.commands.crawl.CrawlerLoop") as loop_cls,
            patch("mobile_crawler.cli.commands.crawl.RunRepository") as run_repo_cls,
            patch("mobile_crawler.cli.commands.crawl.get_app_data_dir") as data_dir,
            patch("mobile_crawler.cli.commands.crawl.ensure_mobsf_running_if_enabled", return_value=None) as mobsf,
            patch("mobile_crawler.cli.commands.crawl.ensure_omniparser_running_if_enabled", return_value=None),
            patch("mobile_crawler.cli.commands.crawl.DeviceDetection") as detection_cls,
            patch(
                "mobile_crawler.cli.commands.crawl.is_package_installed",
                side_effect=lambda device, package: package in installed,
            ),
            patch("mobile_crawler.cli.commands.crawl.ADBActionExecutor") as executor_cls,
        ):
            data_dir.return_value = Mock()
            run_repo = run_repo_cls.return_value
            run_repo.create_run.side_effect = create_run
            run_repo.get_run_by_id.side_effect = get_run_by_id
            config = Mock()
            config.get.side_effect = lambda key, default=None: (
                fallback_setting if key == "human_fallback_enabled" else default
            )
            config_cls.return_value = config
            detection_cls.return_value.get_connected_devices.return_value = [
                Mock(device_id="emulator-5554", is_available=True)
            ]
            args = ["crawl", "--device", "emulator-5554", "--model", "m"]
            for package in packages:
                args += ["--package", package]
            result = CliRunner().invoke(cli, [*args, *extra_args])
        self.created = created
        self.loop_cls = loop_cls
        self.executor_cls = executor_cls
        self.mobsf = mobsf
        self.config = config
        return result

    def _batch_event(self, result):
        events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
        return [e for e in events if e["event"] == "batch_completed"]

    def test_each_package_gets_its_own_run(self):
        result = self._run(["com.a.app", "com.b.app"])

        assert result.exit_code == 0
        assert [r.app_package for r in self.created] == ["com.a.app", "com.b.app"]
        assert [c.args[0] for c in self.loop_cls.return_value.run.call_args_list] == [101, 102]
        assert self.loop_cls.call_count == 2

    def test_each_run_points_features_at_its_own_package(self):
        self._run(["com.a.app", "com.b.app"])

        packages = [c.args[1] for c in self.config.override.call_args_list if c.args[0] == "app_package"]
        assert packages == ["com.a.app", "com.b.app"]

    def test_previous_app_is_force_stopped_between_runs(self):
        self._run(["com.a.app", "com.b.app"])

        self.executor_cls.return_value.force_stop_package.assert_called_once_with("com.a.app")

    def test_docker_autostart_runs_once_per_batch(self):
        self._run(["com.a.app", "com.b.app"])

        self.mobsf.assert_called_once()

    def test_pre_run_warnings_are_checked_once_per_batch(self, no_pre_run_warnings):
        self._run(["com.a.app", "com.b.app"])

        no_pre_run_warnings.assert_called_once()

    def test_summary_is_a_json_event_on_stdout_and_a_table_on_stderr(self):
        result = self._run(["com.a.app", "com.b.app"], installed={"com.a.app"})

        [event] = self._batch_event(result)
        assert event["aborted_reason"] is None
        assert event["runs"] == [
            {"package": "com.a.app", "run_id": 101, "status": "COMPLETED", "stop_reason": "duration_limit"},
            {"package": "com.b.app", "run_id": None, "status": "SKIPPED", "stop_reason": "not installed"},
        ]
        assert "Batch summary" in result.stderr
        assert "com.b.app" in result.stderr and "SKIPPED" in result.stderr

    def test_any_failed_app_makes_the_exit_code_non_zero(self):
        result = self._run(["com.a.app", "com.b.app"], statuses={"com.a.app": ("ERROR", "error: boom")})

        assert result.exit_code == 1
        assert len(self.created) == 2

    def test_single_package_prints_no_batch_summary(self):
        result = self._run(["com.a.app"])

        assert result.exit_code == 0
        assert self._batch_event(result) == []
        assert "Batch summary" not in result.stderr
        self.executor_cls.assert_not_called()

    def test_human_fallback_on_warns_at_batch_start(self):
        result = self._run(["com.a.app", "com.b.app"], fallback_setting=True)

        assert "Human Fallback is on" in result.stderr

    def test_no_human_fallback_flag_silences_the_warning(self):
        result = self._run(["com.a.app", "com.b.app"], ["--no-human-fallback"], fallback_setting=True)

        assert "Human Fallback" not in result.stderr

    def test_human_fallback_off_does_not_warn(self):
        result = self._run(["com.a.app", "com.b.app"], fallback_setting=False)

        assert "Human Fallback" not in result.stderr
