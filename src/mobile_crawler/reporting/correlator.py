from datetime import datetime
from typing import Optional, List, Dict, Any
from .contracts import RunReportData, RunSummary, EnrichedStep, PcapParser, MobSFParser, NetworkRequest

class RunCorrelator:
    def __init__(self, pcap_parser: PcapParser, mobsf_parser: MobSFParser):
        self.pcap_parser = pcap_parser
        self.mobsf_parser = mobsf_parser
    
    def correlate(self, 
                  run_id: str, 
                  run_data: Dict[str, Any], 
                  pcap_path: Optional[str] = None, 
                  mobsf_path: Optional[str] = None) -> RunReportData:
        
        # 1. Parse optional external data
        network_requests = self.pcap_parser.parse(pcap_path) if pcap_path else []
        security_analysis = self.mobsf_parser.parse(mobsf_path) if mobsf_path else None
        
        # 2. Extract run metadata
        start_time = run_data.get('start_time', datetime.now())
        end_time = run_data.get('end_time', datetime.now())
        
        raw_steps = run_data.get('steps', [])
        summary = RunSummary(
            start_time=start_time,
            end_time=end_time,
            duration_seconds=(end_time - start_time).total_seconds(),
            status=run_data.get('status', 'N/A'),
            app_package=run_data.get('package', 'N/A'),
            device_id=run_data.get('device_id', 'N/A'),
            total_steps=len(raw_steps)
        )
        
        # 3. Build Timeline with Correlation (US2)
        timeline = []
        
        # Sort network requests by time for efficient matching (even though PcapParser usually returns them sorted)
        sorted_requests = sorted(network_requests, key=lambda x: x.timestamp)
        
        for i, raw_step in enumerate(raw_steps):
            step_ts = raw_step.get('timestamp', datetime.now())
            
            # Find next step timestamp to define the window
            next_ts = None
            if i + 1 < len(raw_steps):
                next_ts = raw_steps[i+1].get('timestamp')
            else:
                next_ts = end_time  # For the last step, the window ends at the run's end time
            
            # Match requests in this window [step_ts, next_ts)
            step_requests = [
                req for req in sorted_requests 
                if step_ts <= req.timestamp < (next_ts if next_ts else datetime.max)
            ]
            
            timeline.append(EnrichedStep(
                step_number=i + 1,
                timestamp=step_ts,
                action_type=raw_step.get('action', 'N/A'),
                action_details=raw_step.get('details', {}),
                screenshot_path=raw_step.get('screenshot', ''),
                network_requests=step_requests
            ))
            
        return RunReportData(
            run_id=run_id,
            summary=summary,
            timeline=timeline,
            security_analysis=security_analysis,
            network_summary={
                "total_requests": len(network_requests),
                "distinct_hosts": len(set(r.host for r in network_requests)) if network_requests else 0
            }
        )
