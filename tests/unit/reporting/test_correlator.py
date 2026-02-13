import pytest
from datetime import datetime
from mobile_crawler.reporting.correlator import RunCorrelator
from mobile_crawler.reporting.contracts import PcapParser, MobSFParser, MobSFAnalysis

class MockPcapParser(PcapParser):
    def parse(self, path): return []

class MockMobSFParser(MobSFParser):
    def parse(self, path): return MobSFAnalysis(0.0, "N/A", [], [], [])

def test_correlator_basic():
    correlator = RunCorrelator(MockPcapParser(), MockMobSFParser())
    
    run_data = {
        'start_time': datetime(2026, 1, 1, 10, 0, 0),
        'end_time': datetime(2026, 1, 1, 10, 5, 0),
        'status': 'COMPLETED',
        'package': 'com.test',
        'device_id': 'dev1',
        'steps': [
            {'timestamp': datetime(2026, 1, 1, 10, 1, 0), 'action': 'click', 'details': {}, 'screenshot': 's1.png'}
        ]
    }
    
    report = correlator.correlate("run1", run_data)
    
    assert report.run_id == "run1"
    assert report.summary.total_steps == 1
    assert len(report.timeline) == 1
    assert report.summary.duration_seconds == 300.0

from mobile_crawler.reporting.contracts import NetworkRequest

def test_correlator_time_window_matching():
    correlator = RunCorrelator(MockPcapParser(), MockMobSFParser())
    
    # Mock data with network requests
    req1 = NetworkRequest(datetime(2026, 1, 1, 10, 1, 5), "GET", "url1", "h1", "HTTP")
    req2 = NetworkRequest(datetime(2026, 1, 1, 10, 4, 0), "GET", "url2", "h2", "HTTP")
    
    # Inject requests into a mock parse (we'll just use a slightly more advanced mock or manual)
    correlator.pcap_parser.parse = lambda path: [req1, req2]
    
    run_data = {
        'start_time': datetime(2026, 1, 1, 10, 0, 0),
        'end_time': datetime(2026, 1, 1, 10, 5, 0),
        'steps': [
            {'timestamp': datetime(2026, 1, 1, 10, 1, 0), 'action': 'c1'},
            {'timestamp': datetime(2026, 1, 1, 10, 3, 0), 'action': 'c2'},
        ]
    }
    
    report = correlator.correlate("run1", run_data, pcap_path="dummy.pcap")
    
    # Step 1 (10:01:00) should get req1 (10:01:05)
    # Step 2 (10:03:00) should get req2 (10:04:00)
    assert len(report.timeline[0].network_requests) == 1
    assert report.timeline[0].network_requests[0].url == "url1"
    assert len(report.timeline[1].network_requests) == 1
    assert report.timeline[1].network_requests[0].url == "url2"
