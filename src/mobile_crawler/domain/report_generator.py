"""PDF report generator for crawl runs."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import PageBreak

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import RunRepository
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository, StepLog

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates PDF reports for completed crawl runs."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize report generator.

        Args:
            db_manager: Database manager for accessing run data
        """
        self.db_manager = db_manager
        self.run_repository = RunRepository(db_manager)
        self.step_log_repository = StepLogRepository(db_manager)

    def generate(self, run_id: int, output_path: Optional[str] = None) -> str:
        """Generate PDF report for a run.

        Args:
            run_id: ID of the run to generate report for
            output_path: Optional custom output path

        Returns:
            Path to the generated PDF file

        Raises:
            ValueError: If run not found or invalid
        """
        # Get run data
        run = self.run_repository.get_run(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")

        # Get runtime stats
        stats = self._get_runtime_stats(run_id)

        # Get step logs for timeline
        step_logs = self.step_log_repository.get_step_logs_by_run(run_id)

        # Determine output path
        if not output_path:
            output_path = f"crawl_report_run_{run_id}.pdf"

        # Generate PDF
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph("Mobile Crawler Report", title_style))
        story.append(Spacer(1, 12))

        # Run Summary
        story.append(Paragraph("Run Summary", styles['Heading2']))
        summary_data = [
            ["Run ID", str(run.id)],
            ["Device", run.device_id],
            ["App Package", run.app_package],
            ["Start Activity", run.start_activity or "N/A"],
            ["Start Time", run.start_time.strftime("%Y-%m-%d %H:%M:%S")],
            ["End Time", run.end_time.strftime("%Y-%m-%d %H:%M:%S") if run.end_time else "N/A"],
            ["Status", run.status],
            ["AI Provider", run.ai_provider or "N/A"],
            ["AI Model", run.ai_model or "N/A"],
            ["Total Steps", str(run.total_steps)],
            ["Unique Screens", str(run.unique_screens)]
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Statistics Section
        if stats:
            story.append(Paragraph("Crawl Statistics", styles['Heading2']))
            story.append(self._create_stats_section(stats))
            story.append(Spacer(1, 20))

        # Action Timeline
        if step_logs:
            story.append(Paragraph("Action Timeline", styles['Heading2']))
            story.append(self._create_timeline_section(step_logs))
            story.append(Spacer(1, 20))

        # Error Summary
        error_logs = [log for log in step_logs if not log.execution_success]
        if error_logs:
            story.append(Paragraph("Error Summary", styles['Heading2']))
            story.append(self._create_error_section(error_logs))

        # Build PDF
        doc.build(story)
        logger.info(f"Generated report: {output_path}")
        return output_path

    def _get_runtime_stats(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get runtime statistics for a run.

        Args:
            run_id: Run ID

        Returns:
            Stats dictionary or None if not found
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM run_stats WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()

        if not row:
            return None

        # Convert row to dict (assuming column order matches RuntimeStats fields)
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    def _create_stats_section(self, stats: Dict[str, Any]) -> Table:
        """Create statistics section table.

        Args:
            stats: Runtime statistics

        Returns:
            ReportLab Table
        """
        data = [
            ["Metric", "Value"],
            ["Total Steps", stats.get('total_steps', 0)],
            ["Successful Steps", stats.get('successful_steps', 0)],
            ["Failed Steps", stats.get('failed_steps', 0)],
            ["Crawl Duration (s)", f"{stats.get('crawl_duration_seconds', 0):.1f}"],
            ["Avg Step Duration (ms)", f"{stats.get('avg_step_duration_ms', 0):.1f}"],
            ["Unique Screens Visited", stats.get('unique_screens_visited', 0)],
            ["Total Screen Visits", stats.get('total_screen_visits', 0)],
            ["Screens/Minute", f"{stats.get('screens_per_minute', 0):.1f}"],
            ["AI Calls Made", stats.get('total_ai_calls', 0)],
            ["AI Errors", stats.get('ai_error_count', 0)],
            ["Stuck Detections", stats.get('stuck_detection_count', 0)],
            ["Context Losses", stats.get('context_loss_count', 0)]
        ]

        table = Table(data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        return table

    def _create_timeline_section(self, step_logs: List[StepLog]) -> Table:
        """Create action timeline table.

        Args:
            step_logs: List of step logs

        Returns:
            ReportLab Table
        """
        data = [["Step", "Time", "Action", "Target", "Success", "Duration (ms)"]]

        for log in step_logs[:50]:  # Limit to first 50 steps for readability
            time_str = log.timestamp.strftime("%H:%M:%S")
            target = "N/A"
            if log.target_bbox_json:
                try:
                    bbox = json.loads(log.target_bbox_json)
                    target = f"({bbox['top_left'][0]},{bbox['top_left'][1]})"
                except:
                    target = "Parsed"

            data.append([
                str(log.step_number),
                time_str,
                log.action_type,
                target,
                "✓" if log.execution_success else "✗",
                f"{log.action_duration_ms:.0f}" if log.action_duration_ms else "N/A"
            ])

        table = Table(data, colWidths=[0.5*inch, 1*inch, 1.5*inch, 1.5*inch, 0.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        return table

    def _create_error_section(self, error_logs: List[StepLog]) -> Table:
        """Create error summary table.

        Args:
            error_logs: List of failed step logs

        Returns:
            ReportLab Table
        """
        data = [["Step", "Action", "Error Message"]]

        for log in error_logs:
            data.append([
                str(log.step_number),
                log.action_type,
                log.error_message or "Unknown error"
            ])

        table = Table(data, colWidths=[0.5*inch, 1.5*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        return table