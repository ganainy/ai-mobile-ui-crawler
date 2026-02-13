# Contract: VideoRecordingManager

**Feature**: 014-packet-video-analysis  
**Component**: Domain Manager  
**Type**: Internal Interface

## Purpose

Defines the interface for Appium-based video recording during crawl sessions. Handles starting/stopping screen recording, saving video files, and graceful error handling.

## Interface

### Class: `VideoRecordingManager`

```python
class VideoRecordingManager:
    """Manages Appium video recording during crawl sessions."""
    
    def __init__(
        self,
        appium_driver: AppiumDriver,
        config_manager: ConfigManager
    ) -> None:
        """Initialize video recording manager.
        
        Args:
            appium_driver: Appium driver instance
            config_manager: Configuration manager for settings
        """
    
    def start_recording(
        self,
        run_id: Optional[int] = None,
        step_num: Optional[int] = None
    ) -> bool:
        """Start video recording.
        
        Args:
            run_id: Optional run ID for filename generation
            step_num: Optional step number for filename generation
            
        Returns:
            True if recording started successfully, False otherwise
        """
    
    def stop_recording_and_save(self) -> Optional[str]:
        """Stop recording and save video file.
        
        Returns:
            Path to saved video file, or None if recording wasn't started or failed
        """
    
    def is_recording(self) -> bool:
        """Check if recording is currently active.
        
        Returns:
            True if recording, False otherwise
        """
    
    def save_partial_on_crash(self) -> Optional[str]:
        """Attempt to save partial recording on crash.
        
        Can be called in exception handlers to save any available recording data.
        
        Returns:
            Path to partial video file, or None if no recording was active
        """
```

## Configuration Requirements

The manager requires the following configuration keys (via `ConfigManager`):

- `ENABLE_VIDEO_RECORDING`: bool - Enable/disable feature
- `APP_PACKAGE`: str - App package name (for filename generation)

**Note**: Videos are automatically saved to the session directory (via SessionFolderManager). No configurable output directory is needed.

## Behavior

### Start Recording

1. Validates configuration
2. Generates filename with run_id, step_num, timestamp, package
3. Calls Appium driver's `start_recording_screen()` method
4. Sets internal state to recording

### Stop Recording

1. Calls Appium driver's `stop_recording_screen()` method (returns base64 string)
2. Decodes base64 video data
3. Saves to session directory as MP4 file
4. Returns local file path

### Error Handling

- Returns `False` or `None` on failure (never raises exceptions for optional features)
- Logs warnings (not errors) for failures
- Continues crawl execution even if recording fails
- Handles device capability checks (some devices don't support recording)

## Integration Points

- **CrawlerLoop**: Calls `start_recording()` at crawl start, `stop_recording_and_save()` at crawl completion
- **AppiumDriver**: Provides `start_recording_screen()` and `stop_recording_screen()` methods
- **ConfigManager**: Provides configuration values
- **SessionFolderManager**: Resolves output directory paths

## Testing Contract

### Unit Tests

- Test successful start/stop flow
- Test error handling (device doesn't support recording, Appium failure)
- Test configuration validation
- Test filename generation
- Test base64 decoding and file saving
- Test partial save on crash

### Integration Tests

- Test with real device (if available)
- Test with mock Appium driver
- Test video file creation and format
- Test concurrent recording sessions (should be prevented)

## Notes

- Video recording is synchronous (Appium handles async internally)
- Video files can be large (100MB+ for long sessions)
- Device must support Appium video recording capability
- Feature is optional - failures don't stop crawl
- Partial saves are best-effort (may fail if recording corrupted)
