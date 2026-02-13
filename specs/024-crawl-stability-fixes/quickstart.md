# Quickstart: Crawl Stability & Observability Fixes

**Branch**: `024-crawl-stability-fixes` | **Date**: 2026-01-15

## Prerequisites

- Python 3.12 environment
- Existing mobile-crawler development setup
- pytest for running tests

## Implementation Order

Implement fixes in priority order (P1 first, then P2, P3):

### Phase 1: P1 Critical Fixes

#### 1.1 MobSF Extended Timeout (US1)

**Files**: `src/mobile_crawler/infrastructure/mobsf_manager.py`, `src/mobile_crawler/config/defaults.py`

1. Add `mobsf_request_timeout` to defaults.py:
   ```python
   'mobsf_request_timeout': 300,  # 5 minutes for large file downloads
   ```

2. Update `_make_api_request` to use configurable timeout:
   ```python
   def _make_api_request(self, ..., timeout: Optional[int] = None):
       if timeout is None:
           timeout = int(self.config_manager.get('mobsf_request_timeout', 300))
       # Use timeout in requests.get/post
   ```

3. Update `perform_complete_scan` to pass longer timeout for report downloads

**Test**: `pytest tests/unit/test_mobsf_manager.py -v`

#### 1.2 PCAPdroid Stop-Before-Start (US2)

**Files**: `src/mobile_crawler/domain/traffic_capture_manager.py`

1. Add helper method:
   ```python
   async def _stop_any_existing_capture_async(self) -> None:
       """Stop any running capture as precaution."""
       pcapdroid_activity = "com.emanuelef.remote_capture/.activities.CaptureCtrl"
       stop_args = ["shell", "am", "start", "-n", pcapdroid_activity, "-e", "action", "stop"]
       await self._run_adb_command_async(stop_args, suppress_stderr=True)
       await asyncio.sleep(1.0)  # Brief wait for cleanup
   ```

2. Call at start of `start_capture_async`:
   ```python
   async def start_capture_async(self, ...):
       # Always stop any existing capture first
       await self._stop_any_existing_capture_async()
       # ... existing code
   ```

**Test**: Start crawl, force-stop, start new crawl - verify no PCAP conflicts

#### 1.3 Time Mode Duration Fix (US3)

**Files**: `src/mobile_crawler/core/crawler_loop.py`

1. Move config reads from `__init__` to `run()`:
   ```python
   def run(self, run_id: int) -> None:
       # Re-read configuration at run start (ensures UI settings are applied)
       self.max_crawl_steps = self.config_manager.get('max_crawl_steps', 15)
       self.max_crawl_duration_seconds = self.config_manager.get('max_crawl_duration_seconds', 600)
       logger.info(f"Crawl config: max_steps={self.max_crawl_steps}, max_duration={self.max_crawl_duration_seconds}s")
       # ... existing code
   ```

**Test**: Set 300s in UI, verify log shows 300s, verify crawl runs full duration

### Phase 2: P2 User Experience Fixes

#### 2.1 Graceful Stop (US4)

**Files**: `src/mobile_crawler/core/crawler_loop.py`

1. Extract cleanup to helper method:
   ```python
   def _cleanup_crawl_session(self, run_id: int, step_number: int) -> None:
       """Cleanup resources at end of crawl."""
       self._stop_traffic_capture(run_id, step_number)
       self._stop_video_recording()
       # Note: MobSF analysis only if not stopped early
   ```

2. Ensure cleanup is called in all exit paths (already appears correct, just verify)

**Test**: Click Stop during crawl, verify PCAP saved, video saved, no resource leaks

#### 2.2 Pause-Aware Timer (US5)

**Files**: `src/mobile_crawler/core/crawler_loop.py`

1. Add tracking fields in `__init__`:
   ```python
   self._paused_duration = 0.0
   self._pause_start_time: Optional[float] = None
   ```

2. Update `pause()`:
   ```python
   def pause(self) -> None:
       if self.state_machine.state == CrawlState.RUNNING:
           self._pause_start_time = time.time()
           self.state_machine.transition_to(CrawlState.PAUSED_MANUAL)
   ```

3. Update `resume()`:
   ```python
   def resume(self) -> None:
       if self.state_machine.state == CrawlState.PAUSED_MANUAL:
           if self._pause_start_time:
               self._paused_duration += time.time() - self._pause_start_time
               self._pause_start_time = None
           self.state_machine.transition_to(CrawlState.RUNNING)
   ```

4. Track pause in step-by-step wait:
   ```python
   # In step-by-step wait loop
   step_pause_start = time.time()
   while not self._step_advance_event.is_set():
       # ... existing wait logic
   self._paused_duration += time.time() - step_pause_start
   ```

5. Update `_should_continue()`:
   ```python
   elapsed_seconds = time.time() - start_time - self._paused_duration
   ```

**Test**: Set 60s duration, pause for 30s, verify crawl runs for 60s of active time (90s wall clock)

### Phase 3: P3 Observability Improvements

#### 3.1 OCR Statistics (US6)

**Files**: `src/mobile_crawler/core/crawler_loop.py`

1. Add tracking fields in `__init__`:
   ```python
   self._ocr_total_time = 0.0
   self._ocr_operation_count = 0
   ```

2. Accumulate in `_execute_step()` (already has timing):
   ```python
   ocr_start = time.time()
   grounding_overlay = self.grounding_manager.process_screenshot(screenshot_path)
   ocr_duration = time.time() - ocr_start
   
   # Track statistics
   self._ocr_total_time += ocr_duration
   self._ocr_operation_count += 1
   ```

3. Include in completion event:
   ```python
   ocr_avg_ms = (self._ocr_total_time / self._ocr_operation_count * 1000) if self._ocr_operation_count > 0 else 0
   self._emit_event("on_crawl_completed", run_id, step_number - 1, total_duration_ms, reason, {
       "ocr_avg_time_ms": ocr_avg_ms,
       "ocr_total_operations": self._ocr_operation_count,
   })
   ```

4. Display in UI statistics panel (if exists)

**Test**: Run crawl, verify OCR avg time appears in statistics/logs

#### 3.2 Timestamp Verification (US7)

**Files**: Audit only

1. Verify `log_sinks.py` - Already has timestamps ✓
2. Check UI LogViewer shows timestamps
3. Search for any `print()` statements in production code:
   ```bash
   grep -r "print(" src/mobile_crawler --include="*.py" | grep -v "logger\." | grep -v "#"
   ```
4. Replace any found print statements with logger calls

**Test**: Review log output, verify all messages have timestamps

---

## Testing

Run full test suite after each change:
```bash
pytest tests/unit/ -v
pytest tests/integration/ -v
```

Create new integration test file `tests/integration/test_crawl_stability.py` for:
- Pause/resume timer behavior
- Stop button cleanup verification
- Extended duration crawl test

---

## Verification Checklist

- [ ] MobSF analysis for large APKs completes (10+ minutes)
- [ ] No PCAP file conflicts on repeated crawl starts
- [ ] Time-based crawls run for exact configured duration
- [ ] Stop button saves all artifacts
- [ ] Paused time doesn't count toward crawl limit
- [ ] OCR average time visible in statistics
- [ ] All logs have timestamps
