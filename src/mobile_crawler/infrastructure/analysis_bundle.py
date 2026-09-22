"""Analysis Bundle writer: the AI-readable half of a Run Report."""

import json
import logging
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from mobile_crawler.domain.run_config_snapshot import read_config_snapshot
from mobile_crawler.domain.step_phase_models import StepPhaseTransition, build_timing_breakdown
from mobile_crawler.infrastructure.ai_interaction_repository import AIInteractionRepository
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository
from mobile_crawler.infrastructure.screen_repository import ScreenRepository
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository
from mobile_crawler.infrastructure.step_phase_repository import StepPhaseRepository
from mobile_crawler.infrastructure.telemetry_client import TelemetrySummary
from mobile_crawler.reporting.contracts import ReportSection

logger = logging.getLogger(__name__)


class AnalysisBundleWriter:
    """Writes analysis.md, steps.jsonl and run.json for a crawl run.

    Screenshots are referenced by path, never embedded. Full prompts appear only
    in run.json.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.run_repository = RunRepository(db_manager)
        self.step_log_repository = StepLogRepository(db_manager)
        self.screen_repository = ScreenRepository(db_manager)
        self.ai_interaction_repository = AIInteractionRepository(db_manager)
        self.step_phase_repository = StepPhaseRepository(db_manager)

    def write(self, run_id: int, output_dir: Path, telemetry: TelemetrySummary | None = None) -> Path:
        """Write the bundle for a run into output_dir and return that directory.

        Raises:
            ValueError: If the run does not exist.
        """
        run = self.run_repository.get_run_by_id(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")

        output_dir.mkdir(parents=True, exist_ok=True)
        step_logs = self.step_log_repository.get_step_logs_by_run(run_id)
        interactions = self.ai_interaction_repository.get_ai_interactions_by_run(run_id)
        statistics = self._statistics(run_id)
        config = read_config_snapshot(run.session_path)
        phase_transitions = self.step_phase_repository.get_transitions_for_run(run_id)
        timings = self._step_timings(phase_transitions)

        screenshots = {i.step_number: i.screenshot_path for i in interactions}
        logged_steps = {step.step_number: step for step in step_logs}
        steps = [
            self._step_record(run, logged_steps[n], screenshots.get(n), timings.get(n))
            if n in logged_steps
            # Crawls record phase transitions without a step_logs row: export the timing on its own line.
            else self._timing_only_record(n, timings[n])
            for n in sorted(logged_steps.keys() | timings.keys())
        ]

        with open(output_dir / "steps.jsonl", "w", encoding="utf-8") as f:
            for record in steps:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

        run_data = {
            "export_timestamp": datetime.now().isoformat(),
            "run": self._run_metadata(run),
            "screens": self._screens(run_id),
            "step_logs": self._step_logs(step_logs),
            "transitions": self._transitions(run_id),
            "ai_interactions": self._ai_interactions(interactions),
            "step_phase_transitions": [asdict(t) for t in phase_transitions],
            "statistics": statistics,
            "config": config,
            "telemetry": asdict(telemetry) if telemetry else None,
        }
        with open(output_dir / "run.json", "w", encoding="utf-8") as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False, default=str)

        (output_dir / "analysis.md").write_text(
            self._render_markdown(
                run, self._sections(run, statistics, step_logs, interactions, config, timings, telemetry)
            ),
            encoding="utf-8",
        )

        logger.info(f"Analysis bundle for run {run_id} written to: {output_dir}")
        return output_dir

    # -- steps.jsonl -------------------------------------------------------

    # Keys of every steps.jsonl line, in _step_record's order.
    _STEP_RECORD_KEYS = (
        "step_number",
        "timestamp",
        "action_type",
        "action_description",
        "input_text",
        "execution_success",
        "error_message",
        "action_duration_ms",
        "ai_response_time_ms",
        "ai_reasoning",
        "from_screen_id",
        "to_screen_id",
        "screenshot",
        "timing",
    )

    @staticmethod
    def _step_timings(transitions: list[StepPhaseTransition]) -> dict[int, dict[str, Any]]:
        """Timing Breakdown per step number, for steps whose transitions carry timing data."""
        by_step: dict[int, list[StepPhaseTransition]] = defaultdict(list)
        for transition in transitions:
            by_step[transition.step_number].append(transition)
        timings = {step_number: build_timing_breakdown(rows) for step_number, rows in by_step.items()}
        return {step_number: timing for step_number, timing in timings.items() if timing}

    def _step_record(
        self, run: Run, step, screenshot_path: str | None, timing: dict[str, Any] | None
    ) -> dict[str, Any]:
        return {
            "step_number": step.step_number,
            "timestamp": step.timestamp.isoformat() if step.timestamp else None,
            "action_type": step.action_type,
            "action_description": step.action_description,
            "input_text": step.input_text,
            "execution_success": step.execution_success,
            "error_message": step.error_message,
            "action_duration_ms": step.action_duration_ms,
            "ai_response_time_ms": step.ai_response_time_ms,
            "ai_reasoning": step.ai_reasoning,
            "from_screen_id": step.from_screen_id,
            "to_screen_id": step.to_screen_id,
            "screenshot": self._relative_path(run, screenshot_path),
            "timing": timing,
        }

    def _timing_only_record(self, step_number: int, timing: dict[str, Any]) -> dict[str, Any]:
        """A steps.jsonl line for a step that has phase timing but no step_logs row."""
        empty = dict.fromkeys(self._STEP_RECORD_KEYS)
        return {**empty, "step_number": step_number, "timing": timing}

    @staticmethod
    def _relative_path(run: Run, path: str | None) -> str | None:
        if not path:
            return None
        if run.session_path:
            try:
                return os.path.relpath(path, run.session_path).replace(os.sep, "/")
            except ValueError:
                # Different drive on Windows: keep the absolute path.
                return path
        return path

    # -- analysis sections (shared by analysis.md and the HTML report) --------

    def build_sections(self, run_id: int, telemetry: TelemetrySummary | None = None) -> list[ReportSection]:
        """Analysis sections for a run: outcome, summary, config, guided, problems, AI usage."""
        run = self.run_repository.get_run_by_id(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        return self._sections(
            run,
            self._statistics(run_id),
            self.step_log_repository.get_step_logs_by_run(run_id),
            self.ai_interaction_repository.get_ai_interactions_by_run(run_id),
            read_config_snapshot(run.session_path),
            self._step_timings(self.step_phase_repository.get_transitions_for_run(run_id)),
            telemetry,
        )

    def _sections(
        self,
        run: Run,
        statistics: dict[str, Any],
        step_logs,
        interactions,
        config: dict[str, Any] | None,
        timings: dict[int, dict[str, Any]],
        telemetry: TelemetrySummary | None = None,
    ) -> list[ReportSection]:
        sections = [
            self._outcome_section(run),
            self._summary_section(statistics),
            self._config_section(config),
            self._guided_section(run),
            self._repeated_actions_section(step_logs),
            self._failed_steps_section(step_logs),
            self._ai_usage_section(interactions),
            self._timing_section(timings),
            self._telemetry_section(run, telemetry),
        ]
        return [section for section in sections if section is not None]

    @staticmethod
    def _render_markdown(run: Run, sections: list[ReportSection]) -> str:
        lines = [f"# Run {run.id} analysis: {run.app_package}", ""]
        for section in sections:
            lines += [f"## {section.title}", ""]
            if section.intro:
                lines += [section.intro, ""]
            if section.items:
                lines += [f"- {item}" for item in section.items] + [""]
        lines += [
            "Per-step detail is in `steps.jsonl`; full prompts and raw data are in `run.json`.",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def _outcome_section(run: Run) -> ReportSection:
        return ReportSection(
            "Outcome",
            items=[
                f"Status: {run.status}",
                f"Stop reason: {run.stop_reason or 'unknown'}",
                f"Model: {run.ai_provider or 'unknown'} / {run.ai_model or 'unknown'}",
                f"Started: {run.start_time.isoformat() if run.start_time else 'unknown'}",
                f"Ended: {run.end_time.isoformat() if run.end_time else 'unknown'}",
            ],
        )

    @staticmethod
    def _summary_section(statistics: dict[str, Any]) -> ReportSection:
        return ReportSection(
            "Summary",
            items=[
                f"Successful steps: {statistics['successful_actions']} of {statistics['total_steps']}",
                f"Failed steps: {statistics['failed_actions']}",
                f"Unique screens visited: {statistics['unique_screens_visited']}",
                f"AI calls: {statistics['ai_calls']} " f"(avg {(statistics['avg_ai_response_time_ms'] or 0):.0f} ms)",
            ],
        )

    @staticmethod
    def _config_section(config: dict[str, Any] | None) -> ReportSection:
        if not config:
            return ReportSection("Config", intro="No config snapshot was recorded for this run.")
        return ReportSection("Config", items=[f"{key}: {value}" for key, value in config.items()])

    @staticmethod
    def _guided_section(run: Run) -> ReportSection | None:
        if not run.guided_progress_json:
            return None
        try:
            progress = json.loads(run.guided_progress_json)
        except json.JSONDecodeError:
            return None
        items = [f"{i}. {scenario}" for i, scenario in enumerate(progress.get("scenarios", []), 1)]
        items += [
            f"Last subgoal: {progress.get('last_subgoal') or 'none'}",
            f"Last plan: {progress.get('final_plan') or 'none'}",
        ]
        return ReportSection(
            "Guided scenarios",
            intro=("The agent has no per-scenario done signal; the last plan shows what it still " "considered open."),
            items=items,
        )

    @staticmethod
    def _repeated_actions_section(step_logs, min_repeats: int = 3, limit: int = 5) -> ReportSection | None:
        counts = Counter((s.action_type, s.action_description) for s in step_logs)
        repeated = [(key, n) for key, n in counts.most_common() if n >= min_repeats][:limit]
        if not repeated:
            return None
        items = []
        for (action_type, description), n in repeated:
            failures = sum(
                1
                for s in step_logs
                if (s.action_type, s.action_description) == (action_type, description) and not s.execution_success
            )
            items.append(f'{action_type} "{description}": {n} times ({failures} failed)')
        return ReportSection("Repeated actions", intro="Possible stuck loops (same action repeated):", items=items)

    @staticmethod
    def _failed_steps_section(step_logs, limit: int = 20) -> ReportSection | None:
        failed = [s for s in step_logs if not s.execution_success]
        if not failed:
            return None
        items = [
            f'step {s.step_number}: {s.action_type} "{s.action_description}" '
            f"-> {s.error_message or 'no error message'}"
            for s in failed[:limit]
        ]
        if len(failed) > limit:
            items.append(f"... and {len(failed) - limit} more (see `steps.jsonl`)")
        return ReportSection("Failed steps", items=items)

    @staticmethod
    def _ai_usage_section(interactions, limit: int = 10) -> ReportSection | None:
        if not interactions:
            return None
        tokens_in = sum(i.tokens_input or 0 for i in interactions)
        tokens_out = sum(i.tokens_output or 0 for i in interactions)
        latencies = [i.latency_ms for i in interactions if i.latency_ms]
        items = [
            f"Tokens: {tokens_in} input, {tokens_out} output",
            f"AI interactions: {len(interactions)}"
            + (f" (avg latency {sum(latencies) / len(latencies):.0f} ms)" if latencies else ""),
        ]
        errors = [i for i in interactions if not i.success]
        for i in errors[:limit]:
            items.append(f"AI error at step {i.step_number}: {i.error_message or 'unknown error'}")
        return ReportSection("AI usage", items=items)

    @staticmethod
    def _timing_section(timings: dict[int, dict[str, Any]], limit: int = 10) -> ReportSection | None:
        if not timings:
            return None
        durations: dict[tuple[str, str], list[float]] = defaultdict(list)
        retries: list[tuple[int, dict[str, Any]]] = []
        for step_number, timing in sorted(timings.items()):
            for row in timing["phases"]:
                durations[(row["phase"], row["metric"])].append(row["duration_ms"])
            retries += [(step_number, retry) for retry in timing["validation_retries"]]

        items = [
            f"{phase} {metric}: avg {sum(values) / len(values):.0f} ms, "
            f"max {max(values):.0f} ms ({len(values)} steps)"
            for (phase, metric), values in durations.items()
        ]
        items.append(f"Manager validation retries: {len(retries)}")
        for step_number, retry in retries[:limit]:
            attempt = retry.get("attempt")
            prefix = f"step {step_number}" + (f" attempt {attempt}" if attempt is not None else "")
            items.append(f"{prefix}: {retry.get('reason', 'Validation retry')}")
        if len(retries) > limit:
            items.append(f"... and {len(retries) - limit} more (see `steps.jsonl`)")
        return ReportSection(
            "Timing breakdown",
            intro=f"Per-phase durations over {len(timings)} steps with phase data; per-step rows are in `steps.jsonl`.",
            items=items,
        )

    @staticmethod
    def _telemetry_section(run: Run, telemetry: TelemetrySummary | None) -> ReportSection | None:
        if telemetry is None:
            return None
        if telemetry.status == "pending":
            return ReportSection(
                "Telemetry",
                intro=(
                    "Telemetry (Phoenix/Langfuse) is pending: it is only fetched when the report "
                    "is generated manually, so the tracing server has time to ingest the run."
                ),
                items=[f"Trace session id: {run.trace_id}"],
            )
        if telemetry.status != "ok":
            return ReportSection("Telemetry", intro=f"Telemetry unavailable ({telemetry.status}): {telemetry.note}")
        items = [f"Provider: {telemetry.provider}", f"Trace session id: {run.trace_id}"]
        for label, value in (
            ("Traces", telemetry.trace_count),
            ("Spans", telemetry.span_count),
            ("LLM calls", telemetry.llm_calls),
            ("Input tokens", telemetry.tokens_input),
            ("Output tokens", telemetry.tokens_output),
            ("Total cost (USD)", telemetry.total_cost),
        ):
            if value is not None:
                items.append(f"{label}: {value}")
        if telemetry.avg_latency_ms is not None:
            items.append(f"Average latency: {telemetry.avg_latency_ms:.0f} ms")
        if telemetry.link:
            items.append(f"Link: {telemetry.link}")
        items += [f"Error: {error}" for error in telemetry.errors]
        return ReportSection("Telemetry", intro=telemetry.note or None, items=items)

    # -- run.json sections (moved from the former RunExporter) --------------

    def _run_metadata(self, run: Run) -> dict[str, Any]:
        return {
            "id": run.id,
            "device_id": run.device_id,
            "app_package": run.app_package,
            "start_activity": run.start_activity,
            "start_time": run.start_time.isoformat() if run.start_time else None,
            "end_time": run.end_time.isoformat() if run.end_time else None,
            "status": run.status,
            "stop_reason": run.stop_reason,
            "guided_progress_json": run.guided_progress_json,
            "trace_id": run.trace_id,
            "ai_provider": run.ai_provider,
            "ai_model": run.ai_model,
            "total_steps": run.total_steps,
            "unique_screens": run.unique_screens,
        }

    def _screens(self, run_id: int) -> list[dict[str, Any]]:
        return [
            {
                "id": screen.id,
                "composite_hash": screen.composite_hash,
                "visual_hash": screen.visual_hash,
                "screenshot_path": screen.screenshot_path,
                "activity_name": screen.activity_name,
                "first_seen_run_id": screen.first_seen_run_id,
                "first_seen_step": screen.first_seen_step,
            }
            for screen in self.screen_repository.get_screens_by_run(run_id)
        ]

    def _step_logs(self, step_logs) -> list[dict[str, Any]]:
        return [
            {
                "id": step.id,
                "step_number": step.step_number,
                "timestamp": step.timestamp.isoformat() if step.timestamp else None,
                "from_screen_id": step.from_screen_id,
                "to_screen_id": step.to_screen_id,
                "action_type": step.action_type,
                "action_description": step.action_description,
                "target_bbox_json": step.target_bbox_json,
                "input_text": step.input_text,
                "execution_success": step.execution_success,
                "error_message": step.error_message,
                "action_duration_ms": step.action_duration_ms,
                "ai_response_time_ms": step.ai_response_time_ms,
                "ai_reasoning": step.ai_reasoning,
            }
            for step in step_logs
        ]

    def _transitions(self, run_id: int) -> list[dict[str, Any]]:
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT from_screen_id, to_screen_id, action_type, COUNT(*) as count
                FROM transitions
                WHERE run_id = ?
                GROUP BY from_screen_id, to_screen_id, action_type
                ORDER BY count DESC
                """,
                (run_id,),
            )
            return [
                {
                    "from_screen_id": row[0],
                    "to_screen_id": row[1],
                    "action_type": row[2],
                    "count": row[3],
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def _ai_interactions(self, interactions) -> list[dict[str, Any]]:
        return [
            {
                "id": i.id,
                "step_number": i.step_number,
                "timestamp": i.timestamp.isoformat() if i.timestamp else None,
                "screenshot_path": i.screenshot_path,
                "request_prompt": self._clean_request_json(i.request_json),
                "response_raw": i.response_raw,
                "response_parsed_json": i.response_parsed_json,
                "tokens_input": i.tokens_input,
                "tokens_output": i.tokens_output,
                "latency_ms": i.latency_ms,
                "success": i.success,
                "error_message": i.error_message,
            }
            for i in interactions
        ]

    def _clean_request_json(self, request_json: str | None) -> dict | None:
        """Strip base64 screenshot data from a stored request."""
        if not request_json:
            return None
        try:
            request_data = json.loads(request_json)
        except json.JSONDecodeError:
            return {"raw": self._remove_base64(request_json)}

        user_prompt = request_data.get("user_prompt") if isinstance(request_data, dict) else None
        if isinstance(user_prompt, str):
            try:
                prompt_data = json.loads(user_prompt)
                if isinstance(prompt_data, dict) and "screenshot" in prompt_data:
                    prompt_data["screenshot"] = "[BASE64_SCREENSHOT_REMOVED]"
                    request_data["user_prompt"] = json.dumps(prompt_data)
            except json.JSONDecodeError:
                request_data["user_prompt"] = self._remove_base64(user_prompt)
        return request_data

    @staticmethod
    def _remove_base64(text: str) -> str:
        pattern = r'"screenshot"\s*:\s*"[A-Za-z0-9+/=]{100,}"'
        return re.sub(pattern, '"screenshot": "[BASE64_SCREENSHOT_REMOVED]"', text)

    def _statistics(self, run_id: int) -> dict[str, Any]:
        step_stats = self.step_log_repository.get_step_statistics(run_id)
        ai_stats = self.step_log_repository.get_ai_statistics(run_id)

        conn = self.db_manager.get_connection()
        try:
            unique_screens_visited = (
                conn.execute(
                    "SELECT COUNT(DISTINCT to_screen_id) FROM step_logs "
                    "WHERE run_id = ? AND to_screen_id IS NOT NULL",
                    (run_id,),
                ).fetchone()[0]
                or 0
            )
            total_screen_visits = (
                conn.execute(
                    "SELECT COUNT(*) FROM step_logs WHERE run_id = ? AND to_screen_id IS NOT NULL",
                    (run_id,),
                ).fetchone()[0]
                or 0
            )
        finally:
            conn.close()

        return {
            "total_steps": step_stats.get("total_steps", 0),
            "successful_actions": step_stats.get("successful_steps", 0),
            "failed_actions": step_stats.get("failed_steps", 0),
            "unique_screens_visited": unique_screens_visited,
            "total_screen_visits": total_screen_visits,
            "ai_calls": ai_stats.get("ai_calls", 0),
            "avg_ai_response_time_ms": ai_stats.get("avg_response_time_ms", 0.0),
        }
