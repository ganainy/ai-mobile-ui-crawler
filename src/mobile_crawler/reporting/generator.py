import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from .contracts import ReportGenerator, RunReportData


class JinjaReportGenerator(ReportGenerator):
    def __init__(self, template_dir: str = None):
        if template_dir is None:
            # Default to the template dir relative to this file
            template_dir = os.path.join(os.path.dirname(__file__), "templates")

        self.env = Environment(loader=FileSystemLoader(template_dir))

    def generate(self, data: RunReportData, output_path_html: str) -> None:
        """Render and save the HTML report."""
        template = self.env.get_template("report.html.j2")
        html_content = template.render(
            run_id=data.run_id,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            summary=data.summary,
            security_analysis=data.security_analysis,
            timeline=data.timeline,
            network_summary=data.network_summary,
            analysis_sections=data.analysis_sections,
        )

        with open(output_path_html, "w", encoding="utf-8") as f:
            f.write(html_content)
