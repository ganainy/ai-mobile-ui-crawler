# Research: Statistics Display and Crawl Stability

**Feature**: 025-stats-and-stability  
**Date**: 2026-01-16

## Research Questions

### 1. Why does OCR timing only appear in logs and not in the Statistics UI?

**Finding**: OCR timing is already tracked internally in `CrawlerLoop`:
- `_ocr_total_time_ms` and `_ocr_operation_count` accumulate OCR times (lines 107-108)
- The average is calculated and emitted in `_cleanup_crawl_session` via `on_crawl_completed` event
- However, there is **no real-time event** emitted during each step to update the UI

**Decision**: Add a new event `on_ocr_completed` that emits OCR timing after each grounding operation. The `QtSignalAdapter` will forward this to update `CrawlStatistics` and `StatsDashboard` in real-time.

**Rationale**: Using the existing event listener pattern ensures thread safety and consistency.

**Alternatives Considered**:
- Direct callback to UI: Rejected (violates thread safety)
- Polling from UI: Rejected (inefficient and complex)

---

### 2. Why did the crawl complete at 98.8 seconds when configured for 300 seconds?

**Finding**: The `_should_continue` method (lines 403-426) checks:
1. `step_number > self.max_crawl_steps` - If steps exceed limit, crawl stops
2. `active_seconds >= self.max_crawl_duration_seconds` - If duration exceeded, crawl stops

**Root Cause Analysis**:
- Looking at the log: `Crawl completed: 2 steps in 98.8s - Completed successfully`
- The crawl stopped after only 2 steps in 98 seconds
- This suggests the `_execute_step` returned `False` (line 310), which breaks the loop
- The step failed or `signup_completed` was signaled

**Decision**: Add detailed logging in `_execute_step` to track why the loop exited. The reason string in `_get_completion_reason` should be more specific. Also verify that the duration limit check is using the correct configuration value being read from UI.

**Rationale**: The duration limit logic itself appears correct; the issue is likely in step execution or an early exit condition.

**Alternatives Considered**:
- Always run full duration: Rejected (would ignore valid completion reasons)
- Add timeout mechanism: Not needed (duration check exists but early exit masks it)

---

### 3. Why does PCAPdroid show a permission dialog despite API key being configured?

**Finding**: Analyzing `TrafficCaptureManager.start_capture_async`:
- Lines 233-239 show the API key is appended with `-e api_key [KEY]`
- The PCAPdroid documentation states: The API key must be configured **in PCAPdroid app settings first**
- The key passed via intent must **match** the key configured in the app

**Root Cause**: The PCAPdroid app on the device may not have the API control enabled or the key configured in its settings. The mobile-crawler is passing the key, but PCAPdroid doesn't recognize it.

**Decision**: 
1. Add pre-flight validation to check if PCAPdroid API control is enabled
2. Improve error messaging to guide users to configure PCAPdroid correctly
3. Consider adding a configuration check command before starting capture

**Rationale**: The issue is a configuration mismatch, not a code bug.

**Reference**: [PCAPdroid API Documentation](https://github.com/emanuele-f/PCAPdroid/blob/master/docs/app_api.md)

---

### 4. Why does video recording fail to start with "No such process" error?

**Finding**: The error stack trace shows:
```
killall: screenrecord: No such process
```

This occurs in `appium_driver.start_recording_screen()` which internally calls Appium's `startRecordingScreen`. Appium's UIAutomator2 driver tries to kill any existing `screenrecord` process before starting a new one.

**Root Cause**: The cleanup of a previous recording process is erroring because no process exists. This should be handled gracefully.

**Decision**: 
1. Catch the "No such process" error in `start_recording_screen` and treat it as success for cleanup
2. The actual recording start should proceed after this cleanup attempt
3. Add retry logic if the first recording attempt fails

**Rationale**: The error is benign (no process to kill = clean state) but Appium treats it as fatal.

**Implementation Notes**:
- `AppiumDriver.start_recording_screen()` needs a try-except wrapper
- Return `True` if the "No such process" error occurs during pre-cleanup
- Let the actual recording attempt proceed

---

### 5. What timing metrics should be displayed in the Statistics panel?

**Finding**: Current Statistics panel shows (from `stats_dashboard.py` lines 60-123):
- **Crawl Progress**: Total Steps, Actions OK, Actions Failed, Step Progress Bar
- **Screen Discovery**: Unique Screens, Total Visits, Screens/min
- **AI Performance**: AI Calls, Avg Response
- **Duration**: Elapsed, Time Progress Bar

**Missing Metrics** (from spec requirements):
- OCR Average Time
- Action Execution Average Time
- Screenshot Capture Average Time

**Decision**: Add a new "Operation Timing" section to `StatsDashboard` with:
- OCR Avg: Xms
- Action Avg: Xms
- Screenshot Avg: Xms

**Layout Design**:
```
Operation Timing
─────────────────
OCR Avg: 5771ms    Action Avg: 234ms
Screenshot Avg: 156ms
```

**Rationale**: Groups related timing metrics together for easy comparison.

---

### 6. How should running averages be calculated efficiently?

**Finding**: Current approach in `CrawlerLoop`:
- Accumulates total time and count
- Calculates average on demand: `total_time / count`

**Decision**: Use running average with count:
```python
# On each operation:
count += 1
total += new_value
average = total / count
```

This requires only two state variables per metric type and O(1) computation.

**Alternatives Considered**:
- Exponential moving average: Rejected (recent values weighted more, not suitable for final summary)
- Store all values: Rejected (unbounded memory, spec requires efficient calculation)

---

## Summary of Decisions

| Question | Decision |
|----------|----------|
| OCR timing to UI | Add `on_ocr_completed` event with timing |
| Action timing to UI | Add timing to `on_action_executed` event |
| Screenshot timing to UI | Add `on_screenshot_timing` event |
| Early crawl termination | Add detailed logging, improve completion reason |
| PCAPdroid permission | Pre-flight validation, better error messages |
| Video recording | Graceful handling of "No such process" error |
| Statistics layout | New "Operation Timing" section with 3 metrics |
| Average calculation | Running sum/count approach |
