import json
from typing import List
from ..contracts import MobSFParser, MobSFAnalysis, Vulnerability

class JsonMobSFParser(MobSFParser):
    def parse(self, json_report_path: str) -> MobSFAnalysis:
        try:
            with open(json_report_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract basic info
            score = data.get('security_score', 0.0)
            grade = data.get('grade', 'N/A')
            
            # Map findings
            high_issues = self._extract_findings(data, 'high')
            medium_issues = self._extract_findings(data, 'warning') # MobSF often uses 'warning' for medium
            
            # File analysis
            file_analysis = list(data.get('files', {}).keys())
            
            return MobSFAnalysis(
                score=score,
                grade=grade,
                high_issues=high_issues,
                medium_issues=medium_issues,
                file_analysis=file_analysis
            )
        except (FileNotFoundError, json.JSONDecodeError):
            return MobSFAnalysis(0.0, 'ERROR', [], [], [])

    def _extract_findings(self, data: dict, severity_key: str) -> List[Vulnerability]:
        findings = []
        # MobSF JSON structure varies, checking common sections
        # Example: data['findings'] or data['code_analysis']
        # For simplicity in this iteration, we look for a generic findings list if it exists
        raw_findings = data.get('findings', {})
        for key, finding in raw_findings.items():
            if finding.get('severity', '').lower() == severity_key:
                findings.append(Vulnerability(
                    title=finding.get('title', key),
                    description=finding.get('description', ''),
                    severity=finding.get('severity', severity_key),
                    cwe=finding.get('cwe')
                ))
        return findings
