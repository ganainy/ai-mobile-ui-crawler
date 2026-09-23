import json

from mobile_crawler.reporting.parsers.mobsf_parser import JsonMobSFParser
from mobile_crawler.reporting.parsers.pcap_parser import DpktPcapParser


def test_mobsf_parser_reads_appsec_scorecard(tmp_path):
    # Shape of a real MobSF v4 JSON report: findings are lists under "appsec", "files" is a list.
    report_file = tmp_path / "mobsf.json"
    report_file.write_text(json.dumps({
        "files": ["AndroidManifest.xml", "classes.dex"],
        "appsec": {
            "high": [{"title": "MD5 signature", "description": "Signed with MD5.", "section": "certificate"}],
            "warning": [
                {"title": "Exported activity", "description": "a", "section": "manifest"},
                {"title": "Cleartext traffic", "description": "b", "section": "network"},
            ],
            "info": [],
            "security_score": 51,
        },
    }))

    analysis = JsonMobSFParser().parse(str(report_file))

    assert analysis.score == 51
    assert [v.title for v in analysis.high_issues] == ["MD5 signature"]
    assert analysis.high_issues[0].severity == "high"
    assert len(analysis.medium_issues) == 2
    assert analysis.file_analysis == ["AndroidManifest.xml", "classes.dex"]


def test_mobsf_parser_without_appsec(tmp_path):
    report_file = tmp_path / "mobsf.json"
    report_file.write_text(json.dumps({"files": {"a.py": {}}}))

    analysis = JsonMobSFParser().parse(str(report_file))

    assert analysis.score == 0.0
    assert analysis.high_issues == []
    assert analysis.file_analysis == ["a.py"]

def test_pcap_parser_empty(tmp_path):
    # Testing with non-existent file path
    parser = DpktPcapParser()
    requests = parser.parse("non_existent.pcap")
    assert requests == []

# Note: Integration test with real PCAP would be better,
# but for unit test we focus on basic logic/interface compliance.
