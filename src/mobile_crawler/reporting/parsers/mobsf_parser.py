import json

from ..contracts import MobSFAnalysis, MobSFParser, Vulnerability


class JsonMobSFParser(MobSFParser):
    def parse(self, json_report_path: str) -> MobSFAnalysis:
        try:
            with open(json_report_path, encoding='utf-8') as f:
                data = json.load(f)

            # MobSF's JSON report keeps the scorecard under "appsec": the score plus one
            # list of findings per severity ("warning" is MobSF's name for medium).
            appsec = data.get('appsec') or {}
            score = appsec.get('security_score', data.get('security_score', 0.0))
            grade = data.get('grade', 'N/A')

            high_issues = self._extract_findings(appsec, 'high')
            medium_issues = self._extract_findings(appsec, 'warning')

            # "files" is a list of paths in current MobSF, a dict keyed by path in older reports
            file_analysis = list(data.get('files') or [])

            return MobSFAnalysis(
                score=score,
                grade=grade,
                high_issues=high_issues,
                medium_issues=medium_issues,
                file_analysis=file_analysis
            )
        except (FileNotFoundError, json.JSONDecodeError):
            return MobSFAnalysis(0.0, 'ERROR', [], [], [])

    def _extract_findings(self, appsec: dict, severity_key: str) -> list[Vulnerability]:
        return [
            Vulnerability(
                title=finding.get('title', ''),
                description=finding.get('description', ''),
                severity=severity_key,
                cwe=finding.get('cwe'),
            )
            for finding in appsec.get(severity_key) or []
            if isinstance(finding, dict)
        ]
