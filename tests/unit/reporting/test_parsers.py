import pytest
import os
import json
from datetime import datetime
from mobile_crawler.reporting.parsers.pcap_parser import DpktPcapParser
from mobile_crawler.reporting.parsers.mobsf_parser import JsonMobSFParser

def test_mobsf_parser_basic(tmp_path):
    report_file = tmp_path / "mobsf.json"
    dummy_data = {
        "security_score": 85,
        "grade": "B",
        "findings": {
            "finding_1": {
                "title": "Insecure Storage",
                "severity": "high",
                "description": "Data is stored in plain text."
            }
        },
        "files": {"file1.py": {}, "file2.py": {}}
    }
    report_file.write_text(json.dumps(dummy_data))
    
    parser = JsonMobSFParser()
    analysis = parser.parse(str(report_file))
    
    assert analysis.score == 85
    assert analysis.grade == "B"
    assert len(analysis.high_issues) == 1
    assert analysis.high_issues[0].title == "Insecure Storage"
    assert len(analysis.file_analysis) == 2

def test_pcap_parser_empty(tmp_path):
    # Testing with non-existent file path
    parser = DpktPcapParser()
    requests = parser.parse("non_existent.pcap")
    assert requests == []

# Note: Integration test with real PCAP would be better, 
# but for unit test we focus on basic logic/interface compliance.
