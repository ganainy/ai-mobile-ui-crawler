"""Data models for device action verification suite."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(Enum):
    """Types of device actions that can be verified."""
    TAP = "TAP"
    INPUT = "INPUT"
    SWIPE = "SWIPE"
    NAVIGATE = "NAVIGATE"
    DRAG = "DRAG"


class TestStatus(Enum):
    """Status of a verification test result."""
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass
class VerificationCase:
    """Represents a single test scenario to run on the device.

    Attributes:
        name: Unique name of the test case (e.g., "test_tap_coordinates")
        description: Human readable description of what is tested
        action_type: The type of action being tested
        target_element: Locator strategy (e.g., {'text': 'Sign In'})
        expected_result: Condition to verify success (e.g., {'text_visible': 'Login Success'})
        coordinates: Optional (x, y) coordinates for coordinate-based testing
        test_data: Optional test data (e.g., text to input)
    """
    name: str
    description: str
    action_type: ActionType
    target_element: Dict[str, Any]
    expected_result: Dict[str, Any]
    coordinates: Optional[tuple[int, int]] = None
    test_data: Optional[Dict[str, Any]] = None


@dataclass
class TestResult:
    """Result of a single verification test execution.

    Attributes:
        case_name: Reference to VerificationCase name
        status: Pass/Fail/Error/Skipped status
        duration_ms: Time taken to execute in milliseconds
        error_message: Stack trace or failure reason (if failed)
        actual_result: What was actually observed (for debugging)
    """
    case_name: str
    status: TestStatus
    duration_ms: int
    error_message: Optional[str] = None
    actual_result: Optional[Dict[str, Any]] = None


@dataclass
class VerificationReport:
    """The output of a verification run.

    Attributes:
        timestamp: When the run started
        device_info: Connected device metadata
        results: List of individual test outcomes
        summary: Overall Pass/Fail status
        total_duration_ms: Total time for all tests
        passed_count: Number of passed tests
        failed_count: Number of failed tests
        error_count: Number of tests with errors
        skipped_count: Number of skipped tests
    """
    timestamp: datetime = field(default_factory=datetime.utcnow)
    device_info: Dict[str, Any] = field(default_factory=dict)
    results: List[TestResult] = field(default_factory=list)
    summary: str = "UNKNOWN"
    total_duration_ms: int = 0
    passed_count: int = 0
    failed_count: int = 0
    error_count: int = 0
    skipped_count: int = 0

    def add_result(self, result: TestResult) -> None:
        """Add a test result and update summary statistics.

        Args:
            result: The test result to add
        """
        self.results.append(result)
        self.total_duration_ms += result.duration_ms

        if result.status == TestStatus.PASS:
            self.passed_count += 1
        elif result.status == TestStatus.FAIL:
            self.failed_count += 1
        elif result.status == TestStatus.ERROR:
            self.error_count += 1
        elif result.status == TestStatus.SKIPPED:
            self.skipped_count += 1

        self._update_summary()

    def _update_summary(self) -> None:
        """Update the summary status based on results."""
        if self.failed_count > 0 or self.error_count > 0:
            self.summary = "FAIL"
        elif self.passed_count > 0:
            self.summary = "PASS"
        elif self.skipped_count > 0:
            self.summary = "SKIPPED"
        else:
            self.summary = "UNKNOWN"

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the report
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "device_info": self.device_info,
            "summary": self.summary,
            "total_duration_ms": self.total_duration_ms,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "errors": self.error_count,
            "skipped": self.skipped_count,
            "results": [
                {
                    "case_name": r.case_name,
                    "status": r.status.value,
                    "duration_ms": r.duration_ms,
                    "error_message": r.error_message,
                    "actual_result": r.actual_result,
                }
                for r in self.results
            ],
        }
