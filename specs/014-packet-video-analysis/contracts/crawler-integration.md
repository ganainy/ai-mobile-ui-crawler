# Contract: CrawlerLoop Integration

**Feature**: 014-packet-video-analysis  
**Component**: Core Integration  
**Type**: Internal Interface

## Purpose

Defines how feature managers integrate into the crawler loop lifecycle. Specifies initialization, start/stop hooks, and error handling patterns.

## Integration Points

### CrawlerLoop Initialization

```python
class CrawlerLoop:
    def __init__(
        self,
        # ... existing parameters ...
        traffic_capture_manager: Optional[TrafficCaptureManager] = None,
        video_recording_manager: Optional[VideoRecordingManager] = None,
        mobsf_manager: Optional[MobSFManager] = None,
    ):
        """Initialize crawler loop with optional feature managers."""
```

### Lifecycle Hooks

#### 1. Crawl Start

```python
async def run(self, run_id: int) -> None:
    # ... existing initialization ...
    
    # Start traffic capture
    if self.traffic_capture_manager:
        await self.traffic_capture_manager.start_capture_async(run_id, step_num=1)
    
    # Start video recording
    if self.video_recording_manager:
        self.video_recording_manager.start_recording(run_id, step_num=1)
    
    # ... main crawl loop ...
```

#### 2. Crawl Completion

```python
    # ... crawl loop completes ...
    
    # Stop traffic capture
    if self.traffic_capture_manager and self.traffic_capture_manager.is_capturing():
        pcap_path = await self.traffic_capture_manager.stop_capture_and_pull_async(
            run_id, step_number
        )
        if pcap_path:
            logger.info(f"Traffic capture saved: {pcap_path}")
    
    # Stop video recording
    if self.video_recording_manager and self.video_recording_manager.is_recording():
        video_path = self.video_recording_manager.stop_recording_and_save()
        if video_path:
            logger.info(f"Video recording saved: {video_path}")
    
    # Run MobSF analysis (after crawl completes)
    if self.mobsf_manager:
        run = self.run_repository.get_run(run_id)
        if run:
            result = self.mobsf_manager.analyze_package(
                run.app_package,
                run.device_id,
                run_id
            )
            if result.success:
                # Update run with security scores
                self.run_repository.update_run_stats(
                    run_id,
                    mobsf_security_score=result.security_score,
                    mobsf_high_issues=result.high_issues,
                    mobsf_medium_issues=result.medium_issues,
                    mobsf_low_issues=result.low_issues
                )
```

#### 3. Error Handling

```python
except Exception as e:
    # Attempt to save partial video on crash
    if self.video_recording_manager and self.video_recording_manager.is_recording():
        partial_path = self.video_recording_manager.save_partial_on_crash()
        if partial_path:
            logger.warning(f"Partial video saved: {partial_path}")
    
    # Stop traffic capture on error
    if self.traffic_capture_manager and self.traffic_capture_manager.is_capturing():
        try:
            await self.traffic_capture_manager.stop_capture_and_pull_async(run_id, step_number)
        except Exception as capture_error:
            logger.warning(f"Failed to stop traffic capture: {capture_error}")
    
    # Re-raise original exception
    raise
```

## Manager Initialization Pattern

### CLI Integration

```python
# In cli/commands/crawl.py
traffic_manager = None
if config_manager.get('ENABLE_TRAFFIC_CAPTURE', False):
    traffic_manager = TrafficCaptureManager(appium_driver, config_manager)
    traffic_manager.configure(...)

video_manager = None
if config_manager.get('ENABLE_VIDEO_RECORDING', False):
    video_manager = VideoRecordingManager(appium_driver, config_manager)
    video_manager.configure(...)

mobsf_manager = None
if config_manager.get('ENABLE_MOBSF_ANALYSIS', False):
    mobsf_manager = MobSFManager(adb_client, config_manager)
    mobsf_manager.configure(...)

crawler_loop = CrawlerLoop(
    # ... existing parameters ...
    traffic_capture_manager=traffic_manager,
    video_recording_manager=video_manager,
    mobsf_manager=mobsf_manager,
)
```

### UI Integration

```python
# In ui/main_window.py or similar
# Managers initialized in main window setup
# Configuration from UI settings widgets
# Passed to crawler worker thread
```

## Error Handling Contract

### Graceful Degradation

- Feature failures must not stop crawl execution
- Managers return `None` or `False` on failure (never raise exceptions)
- Errors logged as warnings (not errors) for optional features
- Crawl continues even if all features fail

### Validation

- Prerequisites checked before feature initialization
- Configuration validated before use
- Device capabilities checked before starting operations
- Clear error messages provided for troubleshooting

## Threading Considerations

- Traffic capture uses async methods (non-blocking)
- Video recording uses sync methods (Appium handles async)
- MobSF analysis runs after crawl (can be in separate thread)
- All operations should be thread-safe if accessed from multiple threads

## Notes

- Managers are optional - `None` values are acceptable
- Features can be enabled/disabled independently
- Lifecycle hooks are called at appropriate times
- Error handling ensures crawl always completes (even if features fail)
