# Quickstart: Enhanced Report Generation

## Overview
The `reporting` module allows generating comprehensive HTML reports from crawl sessions.

## Usage

```python
from mobile_crawler.reporting.generator import JinjaReportGenerator
from mobile_crawler.reporting.correlator import RunCorrelator
from mobile_crawler.reporting.parsers.pcap_parser import DpktPcapParser
from mobile_crawler.reporting.parsers.mobsf_parser import JsonMobSFParser

# 1. Initialize components
pcap_parser = DpktPcapParser()
mobsf_parser = JsonMobSFParser()
generator = JinjaReportGenerator(template_path="src/mobile_crawler/reporting/templates/report.html.j2")
correlator = RunCorrelator(pcap_parser, mobsf_parser)

# 2. Correlate data
# Assumes 'run_data' is a Run object or dict with basic info and step list
report_data = correlator.correlate(
    run_id="run_22",
    run_data=run_object,
    pcap_path="path/to/traffic.pcap",
    mobsf_path="path/to/mobsf_report.json"
)

# 3. Generate Report
generator.generate(report_data, output_path="path/to/report.html")
```

## Dependencies
- `jinja2`
- `dpkt` 
- `pandas` (optional, may be used internally by correlator)
