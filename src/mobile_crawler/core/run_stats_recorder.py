"""Run Stats recording: fills a RuntimeStatsCollector from crawler events and saves it to run_stats.

Owned by CrawlerLoop, so every front end (GUI and CLI) gets the same persisted statistics.
"""

import json
import logging
from pathlib import Path
from typing import Any

from mobile_crawler.core.crawler_event_listener import CrawlerEventListener
from mobile_crawler.core.runtime_stats_collector import RuntimeStatsCollector
from mobile_crawler.domain.models import ActionResult

logger = logging.getLogger(__name__)


class RunStatsRecorder(CrawlerEventListener):
    """Collects one run's statistics from crawler events; ``save`` writes them once."""

    def __init__(self, run_stats_repository) -> None:
        self._repository = run_stats_repository
        self._collector: RuntimeStatsCollector | None = None
        self._loop_detected_prev = False

    @property
    def collector(self) -> RuntimeStatsCollector | None:
        return self._collector

    def _for_run(self, run_id: int) -> RuntimeStatsCollector | None:
        collector = self._collector
        return collector if collector is not None and collector._run_id == run_id else None

    def on_crawl_started(self, run_id: int, target_package: str) -> None:
        self._collector = RuntimeStatsCollector(run_id=run_id, run_stats_repository=self._repository)
        self._collector.start_session()
        self._collector.set_app_info(app_package=target_package)
        self._loop_detected_prev = False

    def on_action_timing(
        self, run_id: int, step_number: int, action_type: str, success: bool, duration_ms: float
    ) -> None:
        # One executed tool is one step (the numbering step_logs and phase transitions use).
        collector = self._for_run(run_id)
        if collector is None:
            return
        collector.record_step_start()
        if success:
            collector.record_step_success(duration_ms)
        else:
            collector.record_step_failure(duration_ms, f"{action_type} failed")
        collector.record_action(action_type, success, duration_ms)

    def on_screen_processed(
        self, run_id: int, step_number: int, screen_id: int, is_new: bool, visit_count: int, total_screens: int
    ) -> None:
        collector = self._for_run(run_id)
        if collector is not None:
            collector.record_screen_visit(screen_id=screen_id, navigation_depth=step_number)

    def on_ai_response_received(self, run_id: int, step_number: int, response_data: dict[str, Any]) -> None:
        collector = self._for_run(run_id)
        if collector is None:
            return
        success = response_data.get("success", True)
        tokens = (response_data.get("tokens_input") or 0) + (response_data.get("tokens_output") or 0)
        collector.record_ai_call(
            response_time_ms=response_data.get("latency_ms", 0.0) or 0.0, tokens_used=tokens, success=success
        )

        # Each validation retry is one invalid response.
        for _ in range(response_data.get("retry_count", 0) or 0):
            collector.record_ai_retry()
            collector.record_invalid_response()

        call_type = response_data.get("call_type")
        if call_type:
            collector.record_ai_call_type(call_type, success)

        if response_data.get("vision_enabled", True):
            collector.record_vision_call()
        else:
            collector.record_non_vision_call()

        if response_data.get("loop_detected", False):
            collector.record_stuck_detection()
            self._loop_detected_prev = True
        else:
            if self._loop_detected_prev:
                collector.record_stuck_recovery(success=True)
            self._loop_detected_prev = False

    def on_mobsf_finished(
        self, run_id: int, security_score: float, high_issues: int, medium_issues: int, low_issues: int
    ) -> None:
        collector = self._for_run(run_id)
        if collector is not None:
            collector.record_mobsf_results(
                security_score=security_score,
                high_issues=high_issues,
                medium_issues=medium_issues,
                low_issues=low_issues,
            )

    def save(self, run_id: int, session_path: str | None) -> bool:
        """End the session, fold in capture artifacts from the session folder and write run_stats.

        Saves at most once per run; later calls return False.
        """
        collector = self._for_run(run_id)
        if collector is None:
            return False
        self._collector = None
        if session_path:
            try:
                _record_media(collector, Path(session_path))
            except Exception as e:
                logger.debug("Post-crawl media scan skipped: %s", e)
        saved = collector.save()
        if saved:
            logger.info("Saved run_stats for run_id=%s", run_id)
        return saved

    # Events the recorder does not need.
    def on_step_started(self, run_id: int, step_number: int) -> None:
        return None

    def on_screenshot_captured(self, run_id: int, step_number: int, screenshot_path: str) -> None:
        return None

    def on_ai_request_sent(self, run_id: int, step_number: int, request_data: dict[str, Any]) -> None:
        return None

    def on_action_executed(self, run_id: int, step_number: int, action_index: int, result: ActionResult) -> None:
        return None

    def on_step_completed(self, run_id: int, step_number: int, actions_count: int, duration_ms: float) -> None:
        return None

    def on_crawl_completed(self, run_id: int, total_steps: int, total_duration_ms: float, reason: str) -> None:
        return None

    def on_error(self, run_id: int, step_number: int | None, error: Exception) -> None:
        return None

    def on_state_changed(self, run_id: int, old_state: str, new_state: str) -> None:
        return None

    def on_debug_log(self, run_id: int, step_number: int, message: str, level: str = "INFO") -> None:
        return None

    def on_screenshot_timing(self, run_id: int, step_number: int, duration_ms: float) -> None:
        return None


def _record_media(collector: RuntimeStatsCollector, session: Path) -> None:
    """Add the sizes of the run's .pcap / .mp4 outputs (and the video duration) to the stats."""
    pcaps = list(session.rglob("*.pcap"))
    if pcaps:
        collector.record_pcap_stats(file_size_bytes=sum(f.stat().st_size for f in pcaps if f.exists()))

    videos = list(session.rglob("*.mp4"))
    if not videos:
        return
    total = sum(f.stat().st_size for f in videos if f.exists())
    # Duration from manifest.json; stays 0.0 without one rather than being guessed.
    duration_s = 0.0
    manifest = session / "videos" / "manifest.json"
    if manifest.exists():
        try:
            with open(manifest, encoding="utf-8") as fh:
                data = json.load(fh)
            duration_s = float(data.get("total_duration_s") or 0.0)
            if duration_s == 0.0 and "segments" in data:
                duration_s = sum(float(s.get("duration_s", 0) or 0) for s in data.get("segments", []))
        except Exception:
            pass
    collector.record_video_stats(total, duration_s)
