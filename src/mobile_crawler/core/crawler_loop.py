"""DroidRun-backed crawler loop wrapper."""

import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import List, Optional

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.core.crawler_event_listener import CrawlerEventListener
from mobile_crawler.core.log_sinks import LogLevel, capture_stdout_to_ui
from mobile_crawler.domain.droidrun_agent_service import DroidRunAgentService
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
        event_listeners: Optional[List[CrawlerEventListener]] = None
    ):
        """Initialize the DroidRun-backed crawler wrapper.

        Args:
            config_manager: Configuration manager
            run_repository: Repository for runs
            session_folder_manager: SessionFolderManager for artifact organization
            event_listeners: List of event listeners
        """
        self.config_manager = config_manager
        self.run_repository = run_repository
        self.session_folder_manager = session_folder_manager
        self.event_listeners = event_listeners or []

        self._crawl_thread: Optional[threading.Thread] = None
        self._current_run_id: Optional[int] = None
        self._droidrun_agent_service: Optional[DroidRunAgentService] = None
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
                ai_interaction_repository=None,
                device_id=run.device_id
            )

            logs_dir = self.session_folder_manager.get_subfolder(run, "logs")
            self._droidrun_agent_service.configure_run_logging(
                run_id,
                logs_dir,
                self._emit_event,
                True
            )

            exploration_objective = self.config_manager.get("exploration_objective", None)

            # Run both execute and cleanup in the same event loop to ensure proper
            # cleanup of async resources (e.g., google.genai.AsyncClient instances)
            async def run_and_cleanup():
                try:
                    return await self._droidrun_agent_service.execute_exploration_task(
                        run_id=run_id,
                        app_package=run.app_package,
                        max_steps=self.config_manager.get("max_crawl_steps", 15),
                        exploration_objective=exploration_objective
                    )
                finally:
                    # Always cleanup, even if execute fails
                    await self._droidrun_agent_service.cleanup()
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
            if self._cancel_requested:
                status = "STOPPED"
                reason = "Stopped by user"
            elif result.success:
                status = "COMPLETED"
                reason = "DroidRun completed"
            else:
                status = "ERROR"
                reason = result.error_message or "DroidRun failed"

            # Extract action statistics from DroidRun result's final_state
            final_state = result.final_state or {}
            successful_actions = final_state.get('successful_actions', 0)
            failed_actions = final_state.get('failed_actions', 0)
            total_actions = final_state.get('total_actions', 0)

            self.run_repository.update_run_stats(
                run_id=run_id,
                total_steps=result.steps_completed,
                unique_screens=0,
                status=status,
                end_time=datetime.now()
            )

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

        except Exception as e:
            self._transition_state("ERROR", run_id)
            self._emit_event("on_error", run_id, None, e)
        finally:
            if self._droidrun_agent_service:
                self._droidrun_agent_service.clear_run_logging()
                self._droidrun_agent_service = None
            self._transition_state("STOPPED", run_id)

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
        """Emit events to listeners if they implement the method."""
        for listener in list(self.event_listeners):
            handler = getattr(listener, method_name, None)
            if handler:
                try:
                    handler(*args)
                except Exception:
                    continue
