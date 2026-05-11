"""DroidRun-backed crawler loop wrapper."""

import asyncio
import inspect
import json
import logging
import threading
import time
from datetime import datetime
from typing import List, Optional

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.core.crawler_event_listener import CrawlerEventListener
from mobile_crawler.core.log_sinks import LogLevel, capture_stdout_to_ui
from mobile_crawler.domain.droidrun_agent_service import DroidRunAgentService
from mobile_crawler.domain.errors import (
    CrawlerError,
    FatalError,
    RecorderError,
    CheckpointError,
    ErrorContext,
)
from mobile_crawler.domain.traffic_capture_manager import TrafficCaptureManager
from mobile_crawler.domain.video_recording_manager import VideoRecordingManager
from mobile_crawler.infrastructure.mobsf_manager import MobSFManager
from mobile_crawler.infrastructure.run_repository import RunRepository
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager

logger = logging.getLogger(__name__)


class CrawlerLoop:
    """Thin wrapper that delegates traversal to DroidRun."""

    def __init__(
        self,
        config_manager: ConfigManager,
        run_repository: RunRepository,
        session_folder_manager: SessionFolderManager,
        event_listeners: Optional[List[CrawlerEventListener]] = None,
        ai_interaction_repository=None,
    ):
        """Initialize the DroidRun-backed crawler wrapper.

        Args:
            config_manager: Configuration manager
            run_repository: Repository for runs
            session_folder_manager: SessionFolderManager for artifact organization
            event_listeners: List of event listeners
            ai_interaction_repository: Optional repository for AI interaction persistence
        """
        self.config_manager = config_manager
        self.run_repository = run_repository
        self.session_folder_manager = session_folder_manager
        self.event_listeners = event_listeners or []
        self._ai_interaction_repository = ai_interaction_repository

        self._crawl_thread: Optional[threading.Thread] = None
        self._current_run_id: Optional[int] = None
        self._droidrun_agent_service: Optional[DroidRunAgentService] = None
        self._traffic_capture_manager: Optional[TrafficCaptureManager] = None
        self._video_recording_manager: Optional[VideoRecordingManager] = None
        self._cancel_requested = False
        self._state = "IDLE"

    def add_event_listener(self, listener: CrawlerEventListener) -> None:
        """Add an event listener."""
        self.event_listeners.append(listener)

    def remove_event_listener(self, listener: CrawlerEventListener) -> None:
        """Remove an event listener."""
        if listener in self.event_listeners:
            self.event_listeners.remove(listener)

    def start(self, run_id: int) -> None:
        """Start the crawler loop in a background thread.

        Args:
            run_id: The run ID to execute
        """
        if self._crawl_thread and self._crawl_thread.is_alive():
            raise RuntimeError("Crawler is already running")

        self._current_run_id = run_id
        self._crawl_thread = threading.Thread(target=self.run, args=(run_id,), daemon=True)
        self._crawl_thread.start()

    def pause(self) -> None:
        """Pause the crawler."""
        self._emit_event(
            "on_debug_log",
            self._current_run_id or -1,
            0,
            "Pause not supported in DroidRun mode."
        )

    def resume(self) -> None:
        """Resume the crawler."""
        self._emit_event(
            "on_debug_log",
            self._current_run_id or -1,
            0,
            "Resume not supported in DroidRun mode."
        )

    def stop(self) -> None:
        """Stop the crawler."""
        self._cancel_requested = True
        if self._droidrun_agent_service and self._droidrun_agent_service.request_cancel():
            logger.info("Requested cancellation of DroidRun workflow.")

    def is_running(self) -> bool:
        """Check if the crawler is currently running.

        Returns:
            True if crawler thread is active
        """
        return self._crawl_thread is not None and self._crawl_thread.is_alive()

    def set_step_by_step_enabled(self, enabled: bool) -> None:
        """Enable or disable step-by-step mode."""
        self._emit_event(
            "on_debug_log",
            self._current_run_id or -1,
            0,
            "Step-by-step mode not supported in DroidRun mode."
        )

    def is_step_by_step_enabled(self) -> bool:
        """Check if step-by-step mode is enabled."""
        return False

    def advance_step(self) -> None:
        """Advance to the next step when paused in step-by-step mode."""
        self._emit_event(
            "on_debug_log",
            self._current_run_id or -1,
            0,
            "Advance step not supported in DroidRun mode."
        )

    def run(self, run_id: int) -> None:
        """Run the crawler loop for the given run.

        Args:
            run_id: The run ID to execute

        Raises:
            Exception: If the crawl fails
        """
        start_time = time.time()
        self._cancel_requested = False

        try:
            run = self.run_repository.get_run_by_id(run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")

            session_path = self.session_folder_manager.create_session_folder(run_id)
            self.run_repository.update_session_path(run_id, session_path)
            run.session_path = session_path

            self._transition_state("RUNNING", run_id)
            self._emit_event("on_crawl_started", run_id, run.app_package)

            self._droidrun_agent_service = DroidRunAgentService(
                config_manager=self.config_manager,
                ai_interaction_repository=self._ai_interaction_repository,
                device_id=run.device_id
            )

            # Initialize step phase tracking per D-01 (wrap at action level)
            self._droidrun_agent_service.begin_step_tracking(
                run_id=run_id,
                emit_step_phase_event=self._emit_event,
            )

            logs_dir = self.session_folder_manager.get_subfolder(run, "logs")
            self._droidrun_agent_service.configure_run_logging(
                run_id,
                logs_dir,
                self._emit_event,
                True
            )

            exploration_objective = self.config_manager.get("exploration_objective", None)
            
            limit_type = self.config_manager.get("limit_type", "steps")
            max_steps = self.config_manager.get("max_steps", self.config_manager.get("max_crawl_steps", 100))
            max_duration = self.config_manager.get("max_duration_seconds", self.config_manager.get("max_crawl_duration_seconds", 300))
            
            if limit_type == "duration":
                actual_max_steps = 9999
            else:
                actual_max_steps = max_steps

            # Run both execute and cleanup in the same event loop to ensure proper
            # cleanup of async resources (e.g., google.genai.AsyncClient instances)
            async def run_and_cleanup():
                if self.config_manager.get("enable_traffic_capture", False) is True:
                    self._traffic_capture_manager = TrafficCaptureManager(
                        config_manager=self.config_manager,
                        session_folder_manager=self.session_folder_manager,
                        device_id=run.device_id,
                    )
                    try:
                        started, message = await self._traffic_capture_manager.start_capture_async(
                            run_id=run_id,
                            step_num=0,
                            session_path=session_path,
                        )
                        status_text = "started" if started else "not started"
                        self._emit_event(
                            "on_debug_log",
                            run_id,
                            0,
                            f"Traffic capture {status_text}: {message}",
                        )
                    except Exception as e:
                        logger.warning("Failed to start traffic capture: %s", e)
                        self._emit_event(
                            "on_debug_log",
                            run_id,
                            0,
                            f"Traffic capture start failed: {e}",
                        )

                if self.config_manager.get("enable_video_recording", False) is True:
                    self._video_recording_manager = VideoRecordingManager(
                        config_manager=self.config_manager,
                        device_id=run.device_id,
                    )
                    started, message = await self._video_recording_manager.start_recording_async(
                        run_id=run_id,
                        session_path=session_path,
                        app_package=run.app_package,
                    )
                    status_text = "started" if started else "not started"
                    self._emit_event(
                        "on_debug_log",
                        run_id,
                        0,
                        f"Video recording {status_text}: {message}",
                    )
                try:
                    return await self._droidrun_agent_service.execute_exploration_task(
                        run_id=run_id,
                        app_package=run.app_package,
                        max_steps=actual_max_steps,
                        exploration_objective=exploration_objective,
                        max_duration_seconds=max_duration if limit_type == "duration" else None
                    )
                finally:
                    if self._video_recording_manager:
                        try:
                            video_path = await self._video_recording_manager.stop_recording_and_save_async()
                            if video_path:
                                self._emit_event(
                                    "on_debug_log",
                                    run_id,
                                    0,
                                    f"Video recording saved: {video_path}",
                                )
                            else:
                                self._emit_event(
                                    "on_debug_log",
                                    run_id,
                                    0,
                                    "Video recording did not produce a saved segment.",
                                )
                        except Exception as e:
                            logger.warning("Failed to stop video recording: %s", e)
                            self._emit_event(
                                "on_debug_log",
                                run_id,
                                0,
                                f"Video recording stop failed: {e}",
                            )
                        finally:
                            self._video_recording_manager = None

                    if self._traffic_capture_manager:
                        try:
                            pcap_path = await self._traffic_capture_manager.stop_capture_and_pull_async(
                                run_id=run_id,
                                step_num=0,
                            )
                            if pcap_path:
                                self._emit_event(
                                    "on_debug_log",
                                    run_id,
                                    0,
                                    f"Traffic capture saved: {pcap_path}",
                                )
                            else:
                                self._emit_event(
                                    "on_debug_log",
                                    run_id,
                                    0,
                                    "Traffic capture did not produce a saved PCAP.",
                                )
                        except Exception as e:
                            logger.warning("Failed to stop traffic capture: %s", e)
                            self._emit_event(
                                "on_debug_log",
                                run_id,
                                0,
                                f"Traffic capture stop failed: {e}",
                            )
                        finally:
                            self._traffic_capture_manager = None

                    # Always cleanup, even if execute fails
                    cleanup_result = self._droidrun_agent_service.cleanup()
                    if inspect.isawaitable(cleanup_result):
                        await cleanup_result
                    # Force GC of google.genai objects while event loop is still running.
                    # Their __del__ schedules aclose() tasks via create_task(), which only
                    # works while the loop is active.
                    import gc
                    gc.collect()
                    # Drain any __del__-scheduled cleanup tasks before the loop closes
                    pending = [t for t in asyncio.all_tasks()
                               if t is not asyncio.current_task()]
                    if pending:
                        try:
                            await asyncio.wait_for(
                                asyncio.gather(*pending, return_exceptions=True),
                                timeout=5.0
                            )
                        except asyncio.TimeoutError:
                            for task in pending:
                                if not task.done():
                                    task.cancel()

            # Build a UI-callback for stdout lines so DroidRun's print() output
            # (step progress emoji lines, manager/executor responses) appears in the log panel.
            def _ui_log_cb(level: LogLevel, message: str) -> None:
                self._emit_event("on_debug_log", run_id, 0, message)

            with capture_stdout_to_ui(_ui_log_cb):
                result = self._run_async(run_and_cleanup())


            duration_ms = (time.time() - start_time) * 1000
            # Extract action statistics from DroidRun result's final_state
            final_state = result.final_state or {}
            successful_actions = final_state.get('successful_actions', 0)
            failed_actions = final_state.get('failed_actions', 0)
            total_actions = final_state.get('total_actions', 0)
            completion_reason = final_state.get("completion_reason")

            if self._cancel_requested:
                status = "STOPPED"
                reason = "Stopped by user"
            elif result.success:
                status = "COMPLETED"
                reason = completion_reason or "DroidRun completed"
            else:
                status = "ERROR"
                reason = result.error_message or "DroidRun failed"

            self.run_repository.update_run_stats(
                run_id=run_id,
                total_steps=result.steps_completed,
                unique_screens=0,
                status=status,
                end_time=datetime.now()
            )

            if status == "COMPLETED" and self.config_manager.get("enable_mobsf_analysis", False) is True:
                self._run_mobsf_analysis(run, run_id)

            # Emit crawl completed with action stats encoded in reason for backward compatibility
            # Format: "reason | successful=X failed=Y total=Z"
            stats_suffix = f" | successful={successful_actions} failed={failed_actions} total={total_actions}"
            reason_with_stats = reason + stats_suffix

            self._emit_event(
                "on_crawl_completed",
                run_id,
                result.steps_completed,
                duration_ms,
                reason_with_stats,
                0.0
            )

        except CrawlerError as e:
            logger.error(json.dumps(e.to_log_dict()))
            self._transition_state("ERROR", run_id)
            self._emit_event("on_error", run_id, None, e)
        except Exception as e:
            wrapped = FatalError(
                f"Unexpected error: {e}",
                context=ErrorContext(run_id=run_id),
                cause=e,
            )
            logger.error(json.dumps(wrapped.to_log_dict()))
            self._transition_state("ERROR", run_id)
            self._emit_event("on_error", run_id, None, wrapped)
        finally:
            self._video_recording_manager = None
            self._traffic_capture_manager = None
            if self._droidrun_agent_service:
                self._droidrun_agent_service.clear_run_logging()
                self._droidrun_agent_service = None
            self._transition_state("STOPPED", run_id)

    def _run_mobsf_analysis(self, run, run_id: int) -> None:
        """Run MobSF after a successful crawl without affecting crawl completion."""
        self._emit_event("on_debug_log", run_id, 0, "Starting MobSF static analysis...")
        try:
            mobsf_manager = MobSFManager(
                config_manager=self.config_manager,
                session_folder_manager=self.session_folder_manager,
            )
            result = mobsf_manager.analyze_run(run, run.device_id)
            if result.success:
                details = [f"MobSF analysis completed. Hash: {result.scan_id}"]
                if result.json_path:
                    details.append(f"JSON report: {result.json_path}")
                if result.report_path:
                    details.append(f"PDF report: {result.report_path}")
                self._emit_event("on_debug_log", run_id, 0, " | ".join(details))
            else:
                self._emit_event(
                    "on_debug_log",
                    run_id,
                    0,
                    f"MobSF analysis failed: {result.error or 'Unknown error'}",
                )
        except Exception as e:
            logger.warning("MobSF analysis failed for run %s: %s", run_id, e)
            self._emit_event("on_debug_log", run_id, 0, f"MobSF analysis failed: {e}")

    def get_span_stats(self):
        """Return current OTel span stats from the active agent service, or None."""
        svc = self._droidrun_agent_service
        if svc is not None:
            return svc._stats_processor.get_stats()
        return None

    def _run_async(self, coroutine):
        """Run a coroutine in a dedicated event loop."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()

    def _transition_state(self, new_state: str, run_id: Optional[int]) -> None:
        """Update internal state and notify listeners."""
        old_state = self._state
        self._state = new_state
        if run_id is not None:
            self._emit_event("on_state_changed", run_id, old_state, new_state)

    def _emit_event(self, method_name: str, *args) -> None:
        """Emit events to listeners. Recorder/checkpoint failures halt the run."""
        for listener in list(self.event_listeners):
            handler = getattr(listener, method_name, None)
            if handler:
                try:
                    handler(*args)
                except (RecorderError, CheckpointError):
                    # Fail-closed: recorder/checkpoint failure must halt the run
                    raise
                except Exception as e:
                    # Log but don't halt for non-critical listener failures (UI, logging)
                    logger.warning(
                        f"Listener {type(listener).__name__}.{method_name} failed: {e}"
                    )
