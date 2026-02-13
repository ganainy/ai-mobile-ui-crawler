import os
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from .contracts import ReportGenerator, RunReportData

class JinjaReportGenerator(ReportGenerator):
    def __init__(self, template_dir: str = None):
        if template_dir is None:
            # Default to the template dir relative to this file
            template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        
        self.env = Environment(loader=FileSystemLoader(template_dir))
    
    def generate(self, data: RunReportData, output_path_html: str) -> None:
        """Render and save both HTML and JSON reports."""
        # 1. Generate HTML
        template = self.env.get_template('report.html.j2')
        html_content = template.render(
            run_id=data.run_id,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            summary=data.summary,
            security_analysis=data.security_analysis,
            timeline=data.timeline,
            network_summary=data.network_summary
        )
        
        with open(output_path_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        # 2. Generate JSON (Requirement FR-009)
        output_path_json = os.path.splitext(output_path_html)[0] + ".json"
        
        # We need a custom encoder for datetime/timedelta if asdict doesn't handle them
        def datetime_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(output_path_json, 'w', encoding='utf-8') as f:
            json.dump(data.to_dict(), f, indent=2, default=datetime_serializer)
