# Data Model: Enhanced Report Generation

## Entities

### RunReportData
The root aggregation object used to render the report.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | Unique identifier of the run. |
| `summary` | `RunSummary` | High-level metrics (duration, status). |
| `timeline` | `List[EnrichedStep]` | Sequential steps with correlated data. |
| `security_analysis` | `MobSFAnalysis` | Parsed security findings. |
| `network_summary` | `NetworkSummary` | Global network stats (total reqs, distinct domains). |

### RunSummary
| Field | Type | Description |
|-------|------|-------------|
| `start_time` | `datetime` | |
| `end_time` | `datetime` | |
| `duration` | `timedelta` | |
| `status` | `str` | COMPLETED, FAILED, etc. |
| `app_package` | `str` | |
| `device_id` | `str` | |
| `total_steps` | `int` | |

### EnrichedStep
Represents a single step in the crawl, enriched with correlated events.

| Field | Type | Description |
|-------|------|-------------|
| `step_number` | `int` | 1-based index. |
| `timestamp` | `datetime` | When the step started. |
| `action_type` | `str` | click, type, scroll, etc. |
| `action_details` | `Dict` | Coordinates, text, etc. |
| `screenshot_path` | `str` | Relative path to screenshot. |
| `network_requests` | `List[NetworkRequest]` | Requests captured during this step's window. |

### NetworkRequest
Simplified representation of an HTTP/S request extracted from PCAP.

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime` | |
| `method` | `str` | GET, POST, etc. |
| `url` | `str` | Full URL. |
| `host` | `str` | Domain name. |
| `protocol` | `str` | HTTP/1.1, HTTP/2, etc. |
| `status_code` | `Optional[int]` | HTTP Status code (if response captured). |

### MobSFAnalysis
| Field | Type | Description |
|-------|------|-------------|
| `score` | `float` | Security Score (0-100). |
| `grade` | `str` | A, B, C, F. |
| `high_issues` | `List[Vulnerability]` | Critical issues. |
| `medium_issues` | `List[Vulnerability]` | Warning issues. |
| `file_analysis` | `List[str]` | List of analyzed file names. |

### Vulnerability
| Field | Type | Description |
|-------|------|-------------|
| `title` | `str` | e.g., "Insecure Data Storage". |
| `description` | `str` | Detailed explanation. |
| `severity` | `str` | High, Medium, Low. |
| `cwe` | `str` | CWE Identifier (if available). |
