# Contract: MobSFManager

**Feature**: 014-packet-video-analysis  
**Component**: Infrastructure Manager  
**Type**: Internal Interface

## Purpose

Defines the interface for MobSF static analysis integration. Handles APK extraction, upload to MobSF, scan execution, report generation, and result storage.

## Interface

### Class: `MobSFManager`

```python
class MobSFManager:
    """Manages MobSF static analysis integration."""
    
    def __init__(
        self,
        adb_client: Optional[ADBClient] = None,
        config_manager: ConfigManager
    ) -> None:
        """Initialize MobSF manager.
        
        Args:
            adb_client: Optional ADB client for APK extraction
            config_manager: Configuration manager for settings
        """
    
    def analyze_package(
        self,
        package_name: str,
        device_id: str,
        run_id: int
    ) -> MobSFAnalysisResult:
        """Perform complete MobSF analysis workflow.
        
        Args:
            package_name: App package name to analyze
            device_id: Device ID for APK extraction
            run_id: Run ID for report organization
            
        Returns:
            MobSFAnalysisResult with report paths and security score
        """
    
    def extract_apk_from_device(
        self,
        package_name: str,
        device_id: str
    ) -> Optional[str]:
        """Extract APK file from device.
        
        Args:
            package_name: Package name to extract
            device_id: Device ID
            
        Returns:
            Path to extracted APK file, or None if extraction failed
        """
    
    def check_mobsf_available(self) -> Tuple[bool, Optional[str]]:
        """Check if MobSF server is available.
        
        Returns:
            Tuple of (is_available, error_message)
        """
```

### Data Class: `MobSFAnalysisResult`

```python
@dataclass
class MobSFAnalysisResult:
    """Result of MobSF analysis."""
    success: bool
    pdf_report_path: Optional[str] = None
    json_report_path: Optional[str] = None
    security_score: Optional[float] = None
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    error: Optional[str] = None
```

## Configuration Requirements

The manager requires the following configuration keys (via `ConfigManager`):

- `ENABLE_MOBSF_ANALYSIS`: bool - Enable/disable feature
- `MOBSF_API_URL`: str - MobSF API base URL (e.g., `http://localhost:8000/api/v1`)
- `MOBSF_API_KEY`: str - MobSF API key for authentication
- `MOBSF_SCAN_TIMEOUT`: int - Maximum time to wait for scan (seconds, default: 300)
- `MOBSF_POLL_INTERVAL`: int - Interval between status polls (seconds, default: 2)

## Behavior

### Complete Analysis Workflow

1. Extract APK from device using ADB `pm path` and `adb pull`
2. Upload APK to MobSF via REST API
3. Start scan and receive scan ID
4. Poll scan status until completion (with timeout)
5. Download PDF and JSON reports
6. Extract security scorecard
7. Save reports to session directory
8. Return analysis result

### Error Handling

- Returns `MobSFAnalysisResult` with `success=False` on failure
- Logs errors with appropriate severity
- Continues crawl execution even if analysis fails
- Validates MobSF server availability before starting
- Handles network timeouts and retries

## Integration Points

- **CrawlerLoop**: Calls `analyze_package()` after crawl completion
- **ADB**: Executes commands for APK extraction
- **requests library**: HTTP client for MobSF API calls
- **ConfigManager**: Provides configuration values
- **SessionFolderManager**: Resolves output directory paths
- **Database**: Stores security scores in `runs` table

## Testing Contract

### Unit Tests

- Test successful analysis workflow
- Test error handling (MobSF unavailable, network failure, timeout)
- Test APK extraction
- Test API request/response handling
- Test report download and saving
- Test configuration validation

### Integration Tests

- Test with real MobSF server (if available)
- Test with mock MobSF API responses
- Test APK extraction from device
- Test report generation and storage
- Test timeout handling

## Notes

- Analysis is performed after crawl completion (not during)
- Scan can take several minutes for large APKs
- Progress updates should be shown to user during polling
- Reports are saved to session directory with file hash in filename
- Security scores are stored in database for reporting
