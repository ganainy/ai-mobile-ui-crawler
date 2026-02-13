"""Enhanced HTML/JSON report generator for crawl runs."""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import RunRepository
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository
from mobile_crawler.infrastructure.ai_interaction_repository import AIInteractionRepository
from mobile_crawler.reporting.contracts import RunReportData, RunSummary, EnrichedStep, NetworkRequest
from mobile_crawler.reporting.generator import JinjaReportGenerator
from mobile_crawler.reporting.correlator import RunCorrelator
from mobile_crawler.reporting.parsers.pcap_parser import DpktPcapParser
from mobile_crawler.reporting.parsers.mobsf_parser import JsonMobSFParser

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generates enhanced HTML and JSON reports for crawl runs."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize report generator.

        Args:
            db_manager: Database manager for accessing run data
        """
        self.db_manager = db_manager
        self.run_repository = RunRepository(db_manager)
        self.step_log_repository = StepLogRepository(db_manager)
        self.ai_interaction_repository = AIInteractionRepository(db_manager)
        
        # Initialize reporting components
        self.pcap_parser = DpktPcapParser()
        self.mobsf_parser = JsonMobSFParser()
        self.correlator = RunCorrelator(self.pcap_parser, self.mobsf_parser)
        self.jinja_generator = JinjaReportGenerator()

    def generate(self, run_id: int, output_path: Optional[str] = None) -> str:
        """Generate enhanced report for a run.

        Args:
            run_id: ID of the run to generate report for
            output_path: Optional custom output path (HTML)

        Returns:
            Path to the generated HTML file
        """
        # 1. Fetch data from DB
        run = self.run_repository.get_run_by_id(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")

        step_logs = self.step_log_repository.get_step_logs_by_run(run_id)
        
        # 2. Prepare paths for optional artifacts
        pcap_path = None
        mobsf_path = None
        if run.session_path and os.path.exists(run.session_path):
            # Check for PCAP
            pcap_candidate = os.path.join(run.session_path, "traffic", "capture.pcap")
            if os.path.exists(pcap_candidate):
                pcap_path = pcap_candidate
            
            # Check for MobSF JSON
            mobsf_candidate = os.path.join(run.session_path, "mobsf", "report.json")
            if os.path.exists(mobsf_candidate):
                mobsf_path = mobsf_candidate
        
        # 2.2. Fetch AI interactions to get screenshot paths (which are missing in step_logs)
        interactions = self.ai_interaction_repository.get_ai_interactions_by_run(run_id)
        # Map step_number -> screenshot_path
        step_screenshots = {i.step_number: i.screenshot_path for i in interactions}
        
        # 3. Assemble run_data for correlator
        # Map DB model to dictionary expected by correlator
        run_dict = {
            'start_time': run.start_time,
            'end_time': run.end_time or datetime.now(),
            'status': run.status,
            'package': run.app_package,
            'device_id': run.device_id,
            'steps': []
        }
        
        for log in step_logs:
            # Resolve screenshot from AI interactions map
            ss_path = step_screenshots.get(log.step_number)
            
            # Resolve screenshot relative to session folder if possible, or use absolute
            if ss_path and run.session_path and ss_path.startswith(run.session_path):
                 ss_path = os.path.relpath(ss_path, os.path.join(run.session_path, "reports"))

            run_dict['steps'].append({
                'timestamp': log.timestamp,
                'action': log.action_type,
                'details': self._safe_json_load(log.target_bbox_json),
                'screenshot': ss_path
            })

        # 4. Correlate
        report_data = self.correlator.correlate(
            run_id=str(run_id),
            run_data=run_dict,
            pcap_path=pcap_path,
            mobsf_path=mobsf_path
        )

        # 5. Determine output path
        if not output_path:
            filename = f"report_run_{run_id}.html"
            if run.session_path and Path(run.session_path).exists():
                reports_dir = Path(run.session_path) / "reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                output_path = str(reports_dir / filename)
            else:
                output_path = filename

        # 6. Generate
        self.jinja_generator.generate(report_data, output_path)
        
        logger.info(f"Generated enhanced report: {output_path}")
        return output_path

    def _safe_json_load(self, data: Optional[str]) -> Dict[str, Any]:
        """Safely load JSON data, with fallback to ast.literal_eval for older format."""
        if not data:
            return {}
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            try:
                import ast
                return ast.literal_eval(data)
            except:
                return {"raw": data}