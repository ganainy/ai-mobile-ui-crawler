import json
import sys
from datetime import datetime
from typing import Any

import click

from mobile_crawler.config import get_app_data_dir
from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.core.crawler_event_listener import CrawlerEventListener
from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.domain.models import ActionResult
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager


class JSONEventListener(CrawlerEventListener):
    """Event listener that outputs JSON events to stdout."""

    def on_crawl_started(self, run_id: int, target_package: str) -> None:
        """Handle crawl started event."""
        event = {
            "event": "crawl_started",
            "run_id": run_id,
            "target_package": target_package,
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)

    def on_state_changed(self, run_id: int, old_state: str, new_state: str) -> None:
        """Handle state change event."""
        event = {
            "event": "state_changed",
            "run_id": run_id,
            "old_state": old_state,
            "new_state": new_state,
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)

    def on_crawl_completed(
        self,
        run_id: int,
        total_steps: int,
        duration_ms: float,
        reason: str,
        ocr_avg_ms: float = 0.0
    ) -> None:
        """Handle crawl completed event."""
        event = {
            "event": "crawl_completed",
            "run_id": run_id,
            "total_steps": total_steps,
            "duration_ms": duration_ms,
            "reason": reason,
            "ocr_avg_ms": ocr_avg_ms,
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)

    def on_error(self, run_id: int | None, step_number: int | None, error: Exception) -> None:
        """Handle error event."""
        event = {
            "event": "error",
            "run_id": run_id,
            "step_number": step_number,
            "error": str(error),
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)

    def on_step_started(self, run_id: int, step_number: int) -> None:
        """Handle step started event."""
        event = {
            "event": "step_started",
            "run_id": run_id,
            "step_number": step_number,
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)

    def on_screenshot_captured(self, run_id: int, step_number: int, screenshot_path: str) -> None:
        """Handle screenshot captured event."""
        event = {
            "event": "screenshot_captured",
            "run_id": run_id,
            "step_number": step_number,
            "screenshot_path": screenshot_path,
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)

    def on_ai_request_sent(self, run_id: int, step_number: int, request_data: dict[str, Any]) -> None:
        """Handle AI request sent event."""
        event = {
            "event": "ai_request_sent",
            "run_id": run_id,
            "step_number": step_number,
            "request_data": request_data,
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)

    def on_ai_response_received(self, run_id: int, step_number: int, response_data: dict[str, Any]) -> None:
        """Handle AI response received event."""
        event = {
            "event": "ai_response_received",
            "run_id": run_id,
            "step_number": step_number,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
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
                "error_message": result.error_message
            },
            "timestamp": datetime.now().isoformat()
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
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)

    def on_screen_processed(
        self,
        run_id: int,
        step_number: int,
        screen_id: int,
        is_new: bool,
        visit_count: int,
        total_screens: int
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
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)

    def on_debug_log(self, run_id: int, step_number: int, message: str) -> None:
        """Handle debug log event."""
        event = {
            "event": "debug_log",
            "run_id": run_id,
            "step_number": step_number,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)

    def on_ocr_completed(self, run_id: int, step_number: int, duration_ms: float, element_count: int) -> None:
        """Handle OCR completed event."""
        event = {
            "event": "ocr_completed",
            "run_id": run_id,
            "step_number": step_number,
            "duration_ms": duration_ms,
            "element_count": element_count,
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)

    def on_screenshot_timing(self, run_id: int, step_number: int, duration_ms: float) -> None:
        """Handle screenshot timing event."""
        event = {
            "event": "screenshot_timing",
            "run_id": run_id,
            "step_number": step_number,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(event), flush=True)


@click.command()
@click.option('--device', required=True, help='Device ID to crawl')
@click.option('--package', required=True, help='App package name to crawl')
@click.option('--model', required=True, help='AI model to use')
@click.option('--steps', type=int, help='Maximum number of crawl steps')
@click.option('--duration', type=int, help='Maximum crawl duration in seconds')
@click.option('--provider', help='AI provider (gemini, openrouter, ollama)')
@click.option('--enable-traffic-capture', is_flag=True, help='Enable PCAPdroid traffic capture during crawl')
@click.option('--enable-video-recording', is_flag=True, help='Enable video recording during crawl')
@click.option('--enable-mobsf-analysis', is_flag=True, help='Enable MobSF static analysis after crawl')
def crawl(device: str, package: str, model: str, steps: int | None, duration: int | None, provider: str | None, enable_traffic_capture: bool, enable_video_recording: bool, enable_mobsf_analysis: bool) -> None:
    """Start a crawl on the specified device and app."""
    try:
        # Ensure app data directory exists
        app_data_dir = get_app_data_dir()
        app_data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize configuration
        config_manager = ConfigManager()
        config_manager.user_config_store.create_schema()

        # Override config with command line options
        if steps:
            config_manager.set('max_crawl_steps', steps)
        if duration:
            config_manager.set('max_crawl_duration_seconds', duration)
        if provider:
            config_manager.set('ai_provider', provider)
        config_manager.set('ai_model', model)
        config_manager.set('app_package', package)  # Set app package for features
        if enable_traffic_capture:
            config_manager.set('enable_traffic_capture', True)
            config_manager.set('pcapdroid_tls_decryption', True)
        if enable_video_recording:
            config_manager.set('enable_video_recording', True)
        if enable_mobsf_analysis:
            config_manager.set('enable_mobsf_analysis', True)

        # Initialize database
        db_manager = DatabaseManager()
        db_manager.migrate_schema()

        # Create run repository
        run_repo = RunRepository(db_manager)

        # Create run record
        run = Run(
            id=None,
            device_id=device,
            app_package=package,
            start_activity=None,  # Will be determined during crawl
            start_time=datetime.now(),
            end_time=None,
            status='RUNNING',
            ai_provider=provider,
            ai_model=model,
            total_steps=0,
            unique_screens=0
        )
        run_id = run_repo.create_run(run)

        session_folder_manager = SessionFolderManager()
        crawler_loop = CrawlerLoop(
            config_manager=config_manager,
            run_repository=run_repo,
            session_folder_manager=session_folder_manager,
            event_listeners=[JSONEventListener()]
        )

        # Run the crawl
        crawler_loop.run(run_id)

    except Exception as e:
        click.echo(f"Error starting crawl: {e}", err=True)
        sys.exit(1)
