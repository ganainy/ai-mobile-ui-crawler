"""Run Report generator (HTML plus Analysis Bundle) for crawl runs."""

import json
import logging
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from mobile_crawler.domain.run_config_snapshot import read_config_snapshot
from mobile_crawler.domain.run_folder_layout import RunFolderLayout
from mobile_crawler.infrastructure.ai_interaction_repository import AIInteractionRepository
from mobile_crawler.infrastructure.analysis_bundle import AnalysisBundleWriter, screenshots_by_step
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import RunRepository
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository
from mobile_crawler.infrastructure.telemetry_client import (
    TelemetryClient,
    TelemetrySummary,
    fetch_run_telemetry,
)
from mobile_crawler.reporting.correlator import RunCorrelator
from mobile_crawler.reporting.generator import JinjaReportGenerator
from mobile_crawler.reporting.parsers.mobsf_parser import JsonMobSFParser
from mobile_crawler.reporting.parsers.pcap_parser import DpktPcapParser

logger = logging.getLogger(__name__)


class RunFolderMissingError(RuntimeError):
    """The run has no run folder on disk, so there is nowhere to write its Run Report."""


class ReportGenerator:
    """Generates the Run Report (HTML plus Analysis Bundle) for crawl runs."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        telemetry_client_factory: Callable[[str], TelemetryClient | None] | None = None,
    ):
        """Initialize report generator.

        Args:
            db_manager: Database manager for accessing run data
            telemetry_client_factory: Maps a tracing provider name (phoenix/langfuse) to a client
                that can read that provider's data back; None disables telemetry fetching
        """
        self.db_manager = db_manager
        self._telemetry_client_factory = telemetry_client_factory
        self.run_repository = RunRepository(db_manager)
        self.step_log_repository = StepLogRepository(db_manager)
        self.ai_interaction_repository = AIInteractionRepository(db_manager)

        # Initialize reporting components
        self.pcap_parser = DpktPcapParser()
        self.mobsf_parser = JsonMobSFParser()
        self.correlator = RunCorrelator(self.pcap_parser, self.mobsf_parser)
        self.jinja_generator = JinjaReportGenerator()
        self.bundle_writer = AnalysisBundleWriter(db_manager)

    def generate(self, run_id: int, output_path: str | None = None, fetch_telemetry: bool = False) -> str:
        """Generate the Run Report (HTML plus the Analysis Bundle) for a run.

        Args:
            run_id: ID of the run to generate report for
            output_path: Optional custom output path (HTML). The Analysis Bundle still goes to
                the run folder's ``reports/analysis/``, or next to the HTML if the run folder is gone.
            fetch_telemetry: Read the run's Phoenix/Langfuse data back into the report. Off for
                the automatic post-run report, since tracing servers ingest asynchronously.

        Returns:
            Path to the generated HTML file

        Raises:
            ValueError: the run does not exist
            RunFolderMissingError: no output_path given and the run folder is missing
        """
        # 1. Fetch data from DB
        run = self.run_repository.get_run_by_id(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")

        step_logs = self.step_log_repository.get_step_logs_by_run(run_id)

        # 2. Output paths and optional artifacts, all inside the run folder
        layout = RunFolderLayout(run.session_path) if run.session_path else None
        has_run_folder = layout is not None and layout.root.is_dir()
        if has_run_folder:
            html_path = Path(output_path) if output_path else layout.run_report_html
            bundle_dir = layout.analysis_dir
        elif output_path:
            html_path = Path(output_path)
            bundle_dir = html_path.parent / "analysis"
        else:
            raise RunFolderMissingError(
                f"Run {run_id} has no run folder on disk ({run.session_path or 'no path stored'}); "
                "pass an output path to write the report elsewhere"
            )

        pcap_path = None
        mobsf_path = None
        if has_run_folder:
            pcap = layout.find_pcap()
            pcap_path = str(pcap) if pcap else None
            mobsf = layout.find_mobsf_json_report()
            mobsf_path = str(mobsf) if mobsf else None

        # 2.2. Fetch AI interactions to get screenshot paths (which are missing in step_logs)
        interactions = self.ai_interaction_repository.get_ai_interactions_by_run(run_id)
        step_screenshots = screenshots_by_step(step_logs, interactions)

        # 3. Assemble run_data for correlator
        # Map DB model to dictionary expected by correlator
        run_dict = {
            "start_time": run.start_time,
            "end_time": run.end_time or datetime.now(),
            "status": run.status,
            "package": run.app_package,
            "device_id": run.device_id,
            "steps": [],
        }

        for log in step_logs:
            # Resolve screenshot from AI interactions map
            ss_path = step_screenshots.get(log.step_number)

            # Link screenshots relative to the HTML's folder when they are in the run folder
            if ss_path and run.session_path and ss_path.startswith(run.session_path):
                try:
                    ss_path = os.path.relpath(ss_path, html_path.parent)
                except ValueError:  # custom output path on another drive: keep it absolute
                    pass

            run_dict["steps"].append(
                {
                    "timestamp": log.timestamp,
                    "action": log.action_type,
                    "details": self._safe_json_load(log.target_bbox_json),
                    "screenshot": ss_path,
                }
            )

        # 4. Correlate
        report_data = self.correlator.correlate(
            run_id=str(run_id), run_data=run_dict, pcap_path=pcap_path, mobsf_path=mobsf_path
        )

        telemetry = self._telemetry_for(run, fetch_telemetry)
        report_data.analysis_sections = self.bundle_writer.build_sections(run_id, telemetry)

        # 5. Generate
        html_path.parent.mkdir(parents=True, exist_ok=True)
        output_path = str(html_path)
        self.jinja_generator.generate(report_data, output_path)

        logger.info(f"Generated enhanced report: {output_path}")

        # 6. Analysis Bundle (AI-readable half of the Run Report)
        self.bundle_writer.write(run_id, bundle_dir, telemetry)

        return output_path

    def _telemetry_for(self, run, fetch_telemetry: bool) -> TelemetrySummary:
        """Telemetry to embed: pending until fetched, then whatever the tracing server returns."""
        if not fetch_telemetry:
            if run.trace_id:
                return TelemetrySummary(status="pending")
            return fetch_run_telemetry(trace_id=None, client=None)

        config = read_config_snapshot(run.session_path)
        provider = (config or {}).get("tracing_provider") if (config or {}).get("enable_tracing") is True else None
        client = self._telemetry_client_factory(provider) if provider and self._telemetry_client_factory else None
        return fetch_run_telemetry(run.trace_id, client)

    def _safe_json_load(self, data: str | None) -> dict[str, Any]:
        """Safely load JSON data, with fallback to ast.literal_eval for older format."""
        if not data:
            return {}
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            try:
                import ast

                return ast.literal_eval(data)
            except Exception:
                return {"raw": data}
