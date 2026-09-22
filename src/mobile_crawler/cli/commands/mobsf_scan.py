"""CLI command for running MobSF static analysis on a finished run."""

from typing import NoReturn

import click

from mobile_crawler.cli.docker_autostart_report import report_docker_autostart
from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.docker_autostart import ensure_mobsf_running_if_enabled
from mobile_crawler.infrastructure.mobsf_manager import MobSFManager
from mobile_crawler.infrastructure.run_repository import RunRepository
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager


def _fail(message: str) -> NoReturn:
    click.echo(f"Error: {message}", err=True)
    raise click.exceptions.Exit(1)


def _echo_progress(message: str, _color: str | None = None) -> None:
    """Print MobSF progress to stderr, so stdout only carries the result."""
    click.echo(message, err=True)


@click.command("mobsf-scan")
@click.argument("run_id", type=int)
def mobsf_scan(run_id: int):
    """Run MobSF static analysis on a finished run's stored APK.

    Scans the APK saved in the run's session folder (it is only saved if MobSF
    already ran for that run); it never pulls a fresh APK from the device.
    Starts the MobSF Docker container first if it isn't running.

    RUN_ID: ID of the crawl run to scan
    """
    config_manager = ConfigManager()
    db_manager = DatabaseManager()
    db_manager.migrate_schema()

    run = RunRepository(db_manager).get_run_by_id(run_id)
    if run is None:
        _fail(f"Run {run_id} not found")

    if not config_manager.get("enable_mobsf_analysis", False):
        _fail(
            "MobSF analysis is disabled. Enable it with "
            "`mobile-crawler config set enable_mobsf_analysis true`"
        )

    manager = MobSFManager(config_manager, session_folder_manager=SessionFolderManager())
    apk_path = manager.find_stored_apk(run)
    if not apk_path:
        _fail(
            f"Run {run_id} has no stored APK for {run.app_package} in its session folder's apks/. "
            "mobsf-scan only scans APKs saved during the original run (MobSF must have run then, "
            "e.g. with auto_run_mobsf_after_crawl on)."
        )

    report_docker_autostart("MobSF", ensure_mobsf_running_if_enabled(config_manager))

    result = manager.analyze_run(run, run.device_id, apk_path=apk_path, log_callback=_echo_progress)
    if not result.success:
        _fail(f"MobSF analysis failed: {result.error or 'Unknown error'}")

    click.echo(f"MobSF analysis completed for run {run_id}.")
    if result.scan_id:
        click.echo(f"Hash: {result.scan_id}")
    if result.json_path:
        click.echo(f"JSON: {result.json_path}")
    if result.report_path:
        click.echo(f"PDF: {result.report_path}")
    if isinstance(result.security_score, dict) and "score" in result.security_score:
        click.echo(f"Security score: {result.security_score['score']}")
