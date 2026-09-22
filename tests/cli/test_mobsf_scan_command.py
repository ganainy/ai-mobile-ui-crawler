"""Tests for the mobsf-scan CLI command."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from mobile_crawler.cli.main import cli
from mobile_crawler.infrastructure.mobsf_manager import MobSFAnalysisResult

MODULE = "mobile_crawler.cli.commands.mobsf_scan"


def _invoke(
    args,
    run=None,
    enabled=True,
    stored_apk="/session/apks/com.example.app.apk",
    autostart=(True, "MobSF is running"),
    result=None,
):
    """Run mobsf-scan with the database, config, Docker and MobSF manager mocked."""
    if run is None:
        run = Mock(id=5, app_package="com.example.app", device_id="dev1")
    if result is None:
        result = MobSFAnalysisResult(
            success=True,
            report_path="/r/h_report.pdf",
            json_path="/r/h_report.json",
            scan_id="h",
            security_score={"score": 72},
        )
    config = Mock()
    config.get.side_effect = lambda key, default=None: enabled if key == "enable_mobsf_analysis" else default
    with (
        patch(f"{MODULE}.DatabaseManager"),
        patch(f"{MODULE}.ConfigManager", return_value=config),
        patch(f"{MODULE}.SessionFolderManager"),
        patch(f"{MODULE}.RunRepository") as repo_cls,
        patch(f"{MODULE}.MobSFManager") as manager_cls,
        patch(f"{MODULE}.ensure_mobsf_running_if_enabled", return_value=autostart) as autostart_fn,
    ):
        repo_cls.return_value.get_run_by_id.return_value = run
        manager = manager_cls.return_value
        manager.find_stored_apk.return_value = stored_apk
        manager.analyze_run.return_value = result
        outcome = CliRunner().invoke(cli, args)
    return outcome, manager, autostart_fn


class TestMobSFScanCommand:
    def test_help(self):
        result = CliRunner().invoke(cli, ["mobsf-scan", "--help"])

        assert result.exit_code == 0
        assert "RUN_ID" in result.output

    def test_scans_stored_apk_and_prints_report_paths(self):
        result, manager, autostart_fn = _invoke(["mobsf-scan", "5"])

        assert result.exit_code == 0, result.output
        autostart_fn.assert_called_once()
        call = manager.analyze_run.call_args
        assert call.args[1] == "dev1"
        assert call.kwargs["apk_path"] == "/session/apks/com.example.app.apk"
        assert callable(call.kwargs["log_callback"])
        assert "/r/h_report.pdf" in result.stdout
        assert "/r/h_report.json" in result.stdout
        assert "72" in result.stdout

    def test_missing_run_fails_clearly(self):
        with (
            patch(f"{MODULE}.DatabaseManager"),
            patch(f"{MODULE}.ConfigManager"),
            patch(f"{MODULE}.RunRepository") as repo_cls,
            patch(f"{MODULE}.ensure_mobsf_running_if_enabled") as autostart_fn,
        ):
            repo_cls.return_value.get_run_by_id.return_value = None
            result = CliRunner().invoke(cli, ["mobsf-scan", "99"])

        assert result.exit_code != 0
        assert "Run 99 not found" in result.stderr
        autostart_fn.assert_not_called()

    def test_missing_stored_apk_fails_before_starting_docker(self):
        result, manager, autostart_fn = _invoke(["mobsf-scan", "5"], stored_apk=None)

        assert result.exit_code != 0
        assert "no stored APK" in result.stderr
        autostart_fn.assert_not_called()
        manager.analyze_run.assert_not_called()

    def test_disabled_mobsf_fails_with_how_to_enable(self):
        result, manager, autostart_fn = _invoke(["mobsf-scan", "5"], enabled=False)

        assert result.exit_code != 0
        assert "config set enable_mobsf_analysis true" in result.stderr
        autostart_fn.assert_not_called()
        manager.analyze_run.assert_not_called()

    def test_autostart_failure_is_a_warning_and_scan_still_runs(self):
        result, manager, _ = _invoke(["mobsf-scan", "5"], autostart=(False, "Docker not found"))

        assert "Docker not found" in result.stderr
        manager.analyze_run.assert_called_once()

    def test_scan_failure_exits_nonzero_with_error(self):
        result, _, _ = _invoke(
            ["mobsf-scan", "5"], result=MobSFAnalysisResult(success=False, error="Failed to upload APK")
        )

        assert result.exit_code != 0
        assert "Failed to upload APK" in result.stderr

    def test_invalid_run_id_is_rejected(self):
        result = CliRunner().invoke(cli, ["mobsf-scan", "abc"])

        assert result.exit_code != 0
