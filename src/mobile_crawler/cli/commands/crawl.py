import json
import sys
from datetime import datetime
from typing import Any

import click

from mobile_crawler.config import get_app_data_dir
from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.cli.console_reader import ConsoleReader
from mobile_crawler.cli.crawl_batch import BatchResult, run_crawl_batch
from mobile_crawler.cli.step_by_step_console import StepByStepConsole
from mobile_crawler.cli.terminal_human_prompter import TerminalHumanPrompter
from mobile_crawler.core.crawler_event_listener import CrawlerEventListener
from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.core.pre_run_warnings import collect_pre_run_warnings
from mobile_crawler.domain.adb_action_executor import ADBActionExecutor
from mobile_crawler.domain.human_fallback import FALLBACK_ENABLED_KEY
from mobile_crawler.domain.models import ActionResult
from mobile_crawler.domain.report_generator import ReportGenerator
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.device_detection import DeviceDetection
from mobile_crawler.cli.docker_autostart_report import report_docker_autostart
from mobile_crawler.infrastructure.docker_autostart import (
    ensure_mobsf_running_if_enabled,
    ensure_omniparser_running_if_enabled,
)
from mobile_crawler.infrastructure.installed_apps import is_package_installed
from mobile_crawler.infrastructure.run_repository import Run, RunRepository
from mobile_crawler.infrastructure.run_stats_repository import RunStatsRepository
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager
from mobile_crawler.infrastructure.telemetry_client import build_telemetry_client_factory

_LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}


class JSONEventListener(CrawlerEventListener):
    """Event listener that outputs JSON events to stdout."""

    def __init__(self, log_level: str = "INFO") -> None:
        self._min_log_level = _LOG_LEVELS.get(log_level.upper(), 20)

    def on_crawl_started(self, run_id: int, target_package: str) -> None:
        """Handle crawl started event."""
        event = {
            "event": "crawl_started",
            "run_id": run_id,
            "target_package": target_package,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_state_changed(self, run_id: int, old_state: str, new_state: str) -> None:
        """Handle state change event."""
        event = {
            "event": "state_changed",
            "run_id": run_id,
            "old_state": old_state,
            "new_state": new_state,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_crawl_completed(self, run_id: int, total_steps: int, duration_ms: float, reason: str) -> None:
        """Handle crawl completed event."""
        event = {
            "event": "crawl_completed",
            "run_id": run_id,
            "total_steps": total_steps,
            "duration_ms": duration_ms,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_error(self, run_id: int | None, step_number: int | None, error: Exception) -> None:
        """Handle error event."""
        event = {
            "event": "error",
            "run_id": run_id,
            "step_number": step_number,
            "error": str(error),
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_step_started(self, run_id: int, step_number: int) -> None:
        """Handle step started event."""
        event = {
            "event": "step_started",
            "run_id": run_id,
            "step_number": step_number,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_screenshot_captured(self, run_id: int, step_number: int, screenshot_path: str) -> None:
        """Handle screenshot captured event."""
        event = {
            "event": "screenshot_captured",
            "run_id": run_id,
            "step_number": step_number,
            "screenshot_path": screenshot_path,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_ai_request_sent(self, run_id: int, step_number: int, request_data: dict[str, Any]) -> None:
        """Handle AI request sent event."""
        event = {
            "event": "ai_request_sent",
            "run_id": run_id,
            "step_number": step_number,
            "request_data": request_data,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_ai_response_received(self, run_id: int, step_number: int, response_data: dict[str, Any]) -> None:
        """Handle AI response received event."""
        event = {
            "event": "ai_response_received",
            "run_id": run_id,
            "step_number": step_number,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_action_executed(self, run_id: int, step_number: int, action_index: int, result: ActionResult) -> None:
        """Handle action executed event."""
        event = {
            "event": "action_executed",
            "run_id": run_id,
            "step_number": step_number,
            "action_index": action_index,
            "result": {
                "success": result.success,
                "action_type": result.action_type,
                "target": result.target,
                "duration_ms": result.duration_ms,
                "error_message": result.error_message,
            },
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_step_completed(self, run_id: int, step_number: int, actions_count: int, duration_ms: float) -> None:
        """Handle step completed event."""
        event = {
            "event": "step_completed",
            "run_id": run_id,
            "step_number": step_number,
            "actions_count": actions_count,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_screen_processed(
        self, run_id: int, step_number: int, screen_id: int, is_new: bool, visit_count: int, total_screens: int
    ) -> None:
        """Handle screen processed event."""
        event = {
            "event": "screen_processed",
            "run_id": run_id,
            "step_number": step_number,
            "screen_id": screen_id,
            "is_new": is_new,
            "visit_count": visit_count,
            "total_screens": total_screens,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_debug_log(self, run_id: int, step_number: int, message: str, level: str = "INFO") -> None:
        """Handle log event; records below the configured ``--log-level`` are dropped."""
        if _LOG_LEVELS.get(level.upper(), 20) < self._min_log_level:
            return
        event = {
            "event": "debug_log",
            "run_id": run_id,
            "step_number": step_number,
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)

    def on_screenshot_timing(self, run_id: int, step_number: int, duration_ms: float) -> None:
        """Handle screenshot timing event."""
        event = {
            "event": "screenshot_timing",
            "run_id": run_id,
            "step_number": step_number,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(event), flush=True)


_LAST = "last"


def _resolve_last(value: str, config_manager: ConfigManager, key: str, option: str) -> str:
    """Return `value`, or the persisted `key` setting when `value` is 'last' (the GUI's last-used choice)."""
    if value != _LAST:
        return value
    saved = config_manager.user_config_store.get_setting(key, default=None)
    if not saved:
        raise ValueError(f"{option} last: no saved '{key}' setting yet; pass an explicit {option} value")
    return saved


@click.command()
@click.option("--device", required=True, help="Device ID to crawl, or 'last' for the last-used device")
@click.option(
    "--package",
    "packages",
    required=True,
    multiple=True,
    help="App package name to crawl, or 'last' for the last-used app. "
    "Repeat to crawl several apps one after another, each as its own run",
)
@click.option("--model", required=True, help="AI model to use")
@click.option("--steps", type=int, help="Maximum number of crawl steps (per app)")
@click.option("--duration", type=int, help="Maximum crawl duration in seconds (per app)")
@click.option("--provider", help="AI provider (gemini, openrouter, ollama)")
@click.option("--enable-traffic-capture", is_flag=True, help="Enable PCAPdroid traffic capture during crawl")
@click.option("--enable-video-recording", is_flag=True, help="Enable video recording during crawl")
@click.option("--enable-mobsf-analysis", is_flag=True, help="Enable MobSF static analysis after crawl")
@click.option("--no-report", is_flag=True, help="Do not generate the run report after the crawl")
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Minimum level of log events printed to stdout (default: the log_level setting, INFO)",
)
@click.option(
    "--human-fallback/--no-human-fallback",
    default=None,
    help="Override the persisted Human Fallback setting for this run only (default: use the configured setting)",
)
@click.option(
    "--parser-mode",
    type=click.Choice(["accessibility", "boost", "omniparser"], case_sensitive=False),
    help="UI parser mode for this run only (default: the configured UI Parser Mode)",
)
@click.option(
    "--reasoning-mode/--no-reasoning-mode",
    default=None,
    help="Turn the crawler agent's Reasoning Mode on or off for this run only (default: the configured setting)",
)
@click.option(
    "--exploration-objective",
    help="Exploration Objective for this run only (default: the configured objective)",
)
@click.option(
    "--restart-app/--no-restart-app",
    default=None,
    help="Force-stop the app first so the run starts from its launch screen (app data is kept), "
    "or resume where it is, for this run only (default: the configured setting, on)",
)
@click.option(
    "--step-by-step",
    is_flag=True,
    help="Pause after each step, print what it did (on stderr) and wait for Enter before the next one",
)
def crawl(
    device: str,
    packages: tuple[str, ...],
    model: str,
    steps: int | None,
    duration: int | None,
    provider: str | None,
    enable_traffic_capture: bool,
    enable_video_recording: bool,
    enable_mobsf_analysis: bool,
    no_report: bool,
    log_level: str | None,
    human_fallback: bool | None,
    parser_mode: str | None,
    reasoning_mode: bool | None,
    exploration_objective: str | None,
    restart_app: bool | None,
    step_by_step: bool,
) -> None:
    """Start a crawl on the specified device and app, or on several apps one after another."""
    if steps and duration:
        raise click.UsageError("--steps and --duration are mutually exclusive; pass one limit")
    try:
        # Ensure app data directory exists
        app_data_dir = get_app_data_dir()
        app_data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize configuration
        config_manager = ConfigManager()
        config_manager.user_config_store.create_schema()

        device = _resolve_last(device, config_manager, "last_device_id", "--device")
        packages = [_resolve_last(p, config_manager, "last_app_package", "--package") for p in packages]

        # Single-run overrides: never written to the config store.
        if steps:
            config_manager.override("limit_type", "steps")
            config_manager.override("max_steps", steps)
        if duration:
            config_manager.override("limit_type", "duration")
            config_manager.override("max_duration_seconds", duration)
        if provider:
            config_manager.override("ai_provider", provider)
        config_manager.override("ai_model", model)
        if enable_traffic_capture:
            config_manager.override("enable_traffic_capture", True)
            config_manager.override("pcapdroid_tls_decryption", True)
        if enable_video_recording:
            config_manager.override("enable_video_recording", True)
        if enable_mobsf_analysis:
            config_manager.override("enable_mobsf_analysis", True)
            config_manager.override("auto_run_mobsf_after_crawl", True)
        if no_report:
            config_manager.override("auto_generate_report_after_run", False)
        if parser_mode is not None:
            config_manager.override("ui_parser_mode", parser_mode)
        if reasoning_mode is not None:
            config_manager.override("crawler_reasoning_mode", reasoning_mode)
        if exploration_objective is not None:
            config_manager.override("exploration_objective", exploration_objective)
        if restart_app is not None:
            config_manager.override("restart_app_before_run", restart_app)

        effective_log_level = (log_level or config_manager.get("log_level", "INFO") or "INFO").upper()

        report_docker_autostart("MobSF", ensure_mobsf_running_if_enabled(config_manager))
        report_docker_autostart("OmniParser", ensure_omniparser_running_if_enabled(config_manager))

        # stderr: stdout is the JSON event stream.
        for warning in collect_pre_run_warnings(config_manager, device):
            click.echo(f"Warning: {warning.message}", err=True)
            if warning.portal_fix:
                click.echo(
                    f"  Fix: mobile-crawler-cli portal enable --device {device} "
                    "(turns it on over adb; prints the manual steps if that fails)",
                    err=True,
                )

        # Initialize database
        db_manager = DatabaseManager()
        db_manager.migrate_schema()

        # Create run repository
        run_repo = RunRepository(db_manager)

        session_folder_manager = SessionFolderManager()
        # One stdin reader for every prompt in the run, so prompts never race each other for input.
        console_reader = ConsoleReader()

        def make_loop() -> CrawlerLoop:
            crawler_loop = CrawlerLoop(
                config_manager=config_manager,
                run_repository=run_repo,
                session_folder_manager=session_folder_manager,
                event_listeners=[JSONEventListener(effective_log_level)],
                report_generator=ReportGenerator(
                    db_manager,
                    telemetry_client_factory=build_telemetry_client_factory(config_manager),
                ),
                human_prompter=TerminalHumanPrompter(reader=console_reader),
                human_fallback_enabled_override=human_fallback,
                run_stats_repository=RunStatsRepository(db_manager),
            )
            if step_by_step:
                crawler_loop.set_step_by_step_enabled(True)
                crawler_loop.add_event_listener(
                    StepByStepConsole(advance=crawler_loop.advance_step, reader=console_reader)
                )
            return crawler_loop

        crawler = _CliCrawler(device, provider, model, config_manager, run_repo, make_loop)

        if len(packages) == 1:
            run_id = crawler.start_run(packages[0])
            crawler.run(run_id, packages[0])
            return

        fallback_on = human_fallback if human_fallback is not None else bool(config_manager.get(FALLBACK_ENABLED_KEY))
        if fallback_on:
            click.echo(
                "Warning: Human Fallback is on; an unanswered prompt waits out its timeout inside that app's "
                "crawl. Pass --no-human-fallback for unattended batches.",
                err=True,
            )
        result = run_crawl_batch(packages, crawler)
        _report_batch(result)
        sys.exit(result.exit_code)

    except Exception as e:
        click.echo(f"Error starting crawl: {e}", err=True)
        sys.exit(1)


class _CliCrawler:
    """`BatchCrawler` over the real device, the runs table and a fresh CrawlerLoop per run."""

    def __init__(self, device, provider, model, config_manager, run_repo, make_loop) -> None:
        self._device = device
        self._provider = provider
        self._model = model
        self._config_manager = config_manager
        self._run_repo = run_repo
        self._make_loop = make_loop

    def device_ready(self) -> bool:
        return any(d.device_id == self._device and d.is_available for d in DeviceDetection().get_connected_devices())

    def is_installed(self, package: str) -> bool:
        return is_package_installed(self._device, package)

    def force_stop(self, package: str) -> None:
        ADBActionExecutor(self._device).force_stop_package(package)

    def start_run(self, package: str) -> int:
        self._config_manager.override("app_package", package)  # Set app package for features
        run = Run(
            id=None,
            device_id=self._device,
            app_package=package,
            start_activity=None,  # Will be determined during crawl
            start_time=datetime.now(),
            end_time=None,
            status="RUNNING",
            ai_provider=self._provider,
            ai_model=self._model,
            total_steps=0,
            unique_screens=0,
        )
        return self._run_repo.create_run(run)

    def run(self, run_id: int, package: str) -> None:
        self._make_loop().run(run_id)

    def outcome(self, run_id: int) -> tuple[str, str | None]:
        run = self._run_repo.get_run_by_id(run_id)
        if run is None:
            return "ERROR", "error: run not found"
        return run.status, run.stop_reason

    def mark_user_stopped(self, run_id: int) -> None:
        run = self._run_repo.get_run_by_id(run_id)
        if run is None or run.status != "RUNNING":
            return
        self._run_repo.update_run_stats(
            run_id,
            total_steps=run.total_steps,
            unique_screens=run.unique_screens,
            status="STOPPED",
            end_time=datetime.now(),
            stop_reason="user_stop",
        )


def _report_batch(result: BatchResult) -> None:
    """Print the batch summary: one JSON event on stdout, a readable table on stderr."""
    event = {"event": "batch_completed", **result.to_dict(), "timestamp": datetime.now().isoformat()}
    print(json.dumps(event), flush=True)

    width = max(len(e.package) for e in result.entries)
    click.echo("\nBatch summary:", err=True)
    for e in result.entries:
        run = f"run {e.run_id}" if e.run_id is not None else "no run"
        reason = f"  ({e.stop_reason})" if e.stop_reason else ""
        click.echo(f"  {e.package:<{width}}  {run:<10}  {e.status}{reason}", err=True)
    if result.aborted_reason == "device_unreachable":
        click.echo("Batch stopped: the device became unreachable.", err=True)
    elif result.aborted_reason == "user_stop":
        click.echo("Batch stopped by user.", err=True)
