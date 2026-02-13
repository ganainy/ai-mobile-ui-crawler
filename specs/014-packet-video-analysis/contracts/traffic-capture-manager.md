# Contract: TrafficCaptureManager

**Feature**: 014-packet-video-analysis  
**Component**: Domain Manager  
**Type**: Internal Interface

## Purpose

Defines the interface for PCAPDroid traffic capture management during crawl sessions. Handles starting/stopping network traffic capture, pulling PCAP files from device, and graceful error handling.

## Interface

### Class: `TrafficCaptureManager`

```python
class TrafficCaptureManager:
    """Manages PCAPdroid traffic capture during crawl sessions."""
    
    def __init__(
        self, 
        appium_driver: AppiumDriver,
        config_manager: ConfigManager
    ) -> None:
        """Initialize traffic capture manager.
        
        Args:
            appium_driver: Appium driver instance (for device access)
            config_manager: Configuration manager for settings
        """
    
    async def start_capture_async(
        self,
        run_id: Optional[int] = None,
        step_num: Optional[int] = None
    ) -> bool:
        """Start PCAPdroid traffic capture.
        
        Args:
            run_id: Optional run ID for filename generation
            step_num: Optional step number for filename generation
            
        Returns:
            True if capture started successfully, False otherwise
            
        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If PCAPdroid is not installed or accessible
        """
    
    async def stop_capture_and_pull_async(
        self,
        run_id: int,
        step_num: int
    ) -> Optional[str]:
        """Stop capture and pull PCAP file from device.
        
        Args:
            run_id: Run ID for filename generation
            step_num: Step number for filename generation
            
        Returns:
            Path to saved PCAP file, or None if capture wasn't running or failed
        """
    
    def is_capturing(self) -> bool:
        """Check if capture is currently active.
        
        Returns:
            True if capturing, False otherwise
        """
    
    async def get_capture_status_async(self) -> Dict[str, Any]:
        """Get current capture status.
        
        Returns:
            Dictionary with status information:
            - status: str (disabled, running, error, etc.)
            - running: bool
            - error: Optional[str]
        """
```

## Configuration Requirements

The manager requires the following configuration keys (via `ConfigManager`):

- `ENABLE_TRAFFIC_CAPTURE`: bool - Enable/disable feature
- `PCAPDROID_PACKAGE`: str - PCAPdroid app package name
- `PCAPDROID_ACTIVITY`: Optional[str] - Activity name (auto-constructed if not provided)
- `PCAPDROID_API_KEY`: Optional[str] - API key for automated consent
- `TRAFFIC_CAPTURE_OUTPUT_DIR`: str - Output directory path template
- `DEVICE_PCAP_DIR`: str - Device directory for PCAP files (default: `/sdcard/Download/PCAPdroid`)
- `PCAPDROID_INIT_WAIT`: float - Wait time after start (default: 3.0)
- `PCAPDROID_FINALIZE_WAIT`: float - Wait time before pull (default: 2.0)

## Behavior

### Start Capture

1. Validates configuration and PCAPdroid installation
2. Generates filename with run_id, step_num, timestamp, package
3. Sends ADB intent to start PCAPdroid capture
4. Waits for initialization (configurable)
5. Sets internal state to capturing

### Stop Capture

1. Sends ADB intent to stop PCAPdroid capture
2. Waits for finalization (configurable)
3. Pulls PCAP file from device to local path
4. Cleans up device file
5. Returns local file path

### Error Handling

- Returns `False` or `None` on failure (never raises exceptions for optional features)
- Logs warnings (not errors) for failures
- Continues crawl execution even if capture fails
- Validates prerequisites before attempting operations

## Integration Points

- **CrawlerLoop**: Calls `start_capture_async()` at crawl start, `stop_capture_and_pull_async()` at crawl completion
- **ConfigManager**: Provides configuration values
- **SessionFolderManager**: Resolves output directory paths
- **ADB**: Executes commands via subprocess (async wrapper)

## Testing Contract

### Unit Tests

- Test successful start/stop flow
- Test error handling (PCAPdroid not installed, ADB failure)
- Test configuration validation
- Test filename generation
- Test async command execution

### Integration Tests

- Test with real device (if available)
- Test with mock ADB commands
- Test file pull and cleanup
- Test concurrent capture sessions (should be prevented)

## Notes

- All ADB operations are async to avoid blocking crawl loop
- PCAP files are automatically cleaned up from device after pull
- Feature is optional - failures don't stop crawl
- Status queries are limited by ADB interaction (may not be real-time)
