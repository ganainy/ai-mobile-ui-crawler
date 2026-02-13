import os
from datetime import datetime
from mobile_crawler.reporting.generator import JinjaReportGenerator
from mobile_crawler.reporting.contracts import RunReportData, RunSummary, MobSFAnalysis

def test_generator_creates_files(tmp_path):
    output_html = tmp_path / "report.html"
    output_json = tmp_path / "report.json"
    
    data = RunReportData(
        run_id="test_run",
        summary=RunSummary(
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration_seconds=10.0,
            status="COMPLETED",
            app_package="com.test",
            device_id="dev123",
            total_steps=0
        ),
        timeline=[],
        security_analysis=None,
        network_summary={}
    )
    
    generator = JinjaReportGenerator()
    generator.generate(data, str(output_html))
    
    assert os.path.exists(output_html)
    assert os.path.exists(output_json)
    
    # Verify content
    with open(output_json, 'r') as f:
        json_data = f.read()
        assert '"run_id": "test_run"' in json_data
