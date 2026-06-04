from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class NetworkRequest:
    timestamp: datetime
    method: str
    url: str
    host: str
    protocol: str
    status_code: int | None = None

@dataclass
class Vulnerability:
    title: str
    description: str
    severity: str
    cwe: str | None = None

@dataclass
class MobSFAnalysis:
    score: float
    grade: str
    high_issues: list[Vulnerability]
    medium_issues: list[Vulnerability]
    file_analysis: list[str]

@dataclass
class EnrichedStep:
    step_number: int
    timestamp: datetime
    action_type: str
    action_details: dict[str, Any]
    screenshot_path: str
    network_requests: list[NetworkRequest]

@dataclass
class RunSummary:
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    status: str
    app_package: str
    device_id: str
    total_steps: int

@dataclass
class RunReportData:
    run_id: str
    summary: RunSummary
    timeline: list[EnrichedStep]
    security_analysis: MobSFAnalysis | None
    network_summary: dict[str, Any]

class PcapParser(ABC):
    """Contract for parsing network traffic files."""

    @abstractmethod
    def parse(self, pcap_path: str) -> list[NetworkRequest]:
        """Parse a PCAP file and extract HTTP/S requests."""
        pass

class MobSFParser(ABC):
    """Contract for parsing security reports."""

    @abstractmethod
    def parse(self, json_report_path: str) -> MobSFAnalysis:
        """Parse a MobSF JSON report."""
        pass

class ReportGenerator(ABC):
    """Contract for generating the final report artifact."""

    @abstractmethod
    def generate(self, data: RunReportData, output_path: str) -> None:
        """Render and save the report to the specified path."""
        pass
