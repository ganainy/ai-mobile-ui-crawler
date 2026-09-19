# Crawl Duration Analysis: 5-Step OmniParser Runs

Analysis date: 2026-06-06

## Summary

Two 5-step crawls were compared:

- Local OmniParser run 106: 5 steps in about 534.5 seconds.
- Replicate OmniParser run 107: 5 steps in about 192.1 seconds.

Replicate is much faster than the local OmniParser setup in these logs, but the crawl is still slow for only 5 actions because `ui_parser_mode=omniparser` forces vision parsing on every UI state capture. The runtime also performs more than one state capture in several steps, and it captures one final UI state after the step limit is reached.

The Replicate run also shows intermittent screenshot capture errors:

```text
Invalid PNG screenshot on attempt 1/3: truncated PNG file
Invalid PNG screenshot on attempt 1/3: broken PNG file (chunk b'\x00\x00\x00\x00')
Invalid PNG screenshot on attempt 1/3: ('open failed: No such file or directory', '/data/local/tmp/adbutils-tmp41704.png')
```

Those errors are retried successfully, but they point to a fragile screenshot capture path using `async_adbutils.device.screenshot_bytes()`.

## Run Comparison

| Metric | Local OmniParser | Replicate OmniParser |
| --- | ---: | ---: |
| Run id | 106 | 107 |
| Total duration | 534.5s | 192.1s |
| Backend | `local` | `replicate` |
| Parser mode | `omniparser` | `omniparser` |
| Feature flags | traffic/video/MobSF disabled | traffic/video/MobSF disabled |
| Typical parse duration from logs | ~28-56s | ~5-10s |
| Final post-limit parse | Yes, ~37s | Yes, ~6s |

Replicate reduced the total runtime by about 64%, but 192 seconds for 5 steps is still high because the crawler is repeatedly doing screenshot capture, OmniParser inference, Manager LLM reasoning, Executor LLM action selection, and post-action checks.

## Replicate Run Timing

| Phase | Log window | Approx. duration | Notes |
| --- | --- | ---: | --- |
| Startup before step loop | 02:50:46-02:50:47 | 1s | Device already active; agent and LLM profiles initialize quickly. |
| Step 1 | 02:50:47-02:51:20 | 33s | Replicate parse ~9s, Manager ~14s, Executor ~9s. |
| Step 2 | 02:51:20-02:51:56 | 36s | Screenshot retry errors, then two Replicate parses: ~6s and ~9s. |
| Step 3 | 02:51:56-02:52:29 | 33s | Screenshot retry errors, then two Replicate parses: ~5s and ~6s. |
| Step 4 | 02:52:29-02:53:14 | 45s | Two Replicate parses: ~6s and ~7s; Executor took ~16s. |
| Step 5 | 02:53:14-02:53:51 | 37s | Screenshot retry error, two Replicate parses: ~5s and ~6s. |
| Post-limit final capture | 02:53:51-02:53:58 | 7s | Final UI state capture after `Reached maximum steps (5)`. |

The Replicate run confirms that local model speed was a major contributor to run 106, but it also confirms the architecture issue: multiple parser calls are still happening per step.

## Evidence From The Local Run

Local run 106 used:

- `ui_parser_mode = omniparser`
- `omniparser_backend = local`
- `omniparser_local_url = http://localhost:8000`
- `omniparser_local_parse_timeout_seconds = 120`

Observed local run timing:

| Phase | Log window | Approx. duration | Notes |
| --- | --- | ---: | --- |
| Startup before step loop | 02:33:16-02:33:22 | 6s | Device wake, target app check, agent setup. |
| Step 1 | 02:33:22-02:34:29 | 67s | First local OmniParser parse finishes at 02:34:03; Manager and Executor then run. |
| Step 2 | 02:34:30-02:35:53 | 83s | Two `Using OmniParser only` logs appear at 02:35:02 and 02:35:33. |
| Step 3 | 02:35:53-02:37:52 | 119s | Two parses at 02:36:21 and 02:36:50, then a long Manager response ending 02:37:45. |
| Step 4 | 02:37:52-02:39:24 | 92s | Two parses at 02:38:28 and 02:39:00. |
| Step 5 | 02:39:25-02:41:34 | 129s | Two parses at 02:40:21 and 02:41:16. |
| Post-limit final capture | 02:41:34-02:42:11 | 37s | Final UI state capture after `Reached maximum steps (5)`. |

Traffic capture, video recording, and MobSF analysis were disabled in both runs, so they are not responsible for the duration.

## What In The Code Causes This

### 1. `omniparser` mode forces vision parsing on every state capture

`AndroidStateProvider.get_state()` always captures a screenshot and, when `ui_parser_mode == "omniparser"`, calls `_get_omni_parser_elements()` before formatting the UI state.

Relevant code:

- `src/mobile_crawler/domain/crawler_agent/tools/ui/provider.py:185` starts `AndroidStateProvider.get_state()`.
- `src/mobile_crawler/domain/crawler_agent/tools/ui/provider.py:220` calls `_get_omni_parser_elements(screenshot_bytes)` in `omniparser` mode.
- `src/mobile_crawler/domain/crawler_agent/tools/ui/provider.py:223` logs `Using OmniParser only (...)`.

Because both pasted runs use `omniparser`, accessibility data is ignored even when it exists. The faster `boost` mode would use accessibility first and only fall back to OmniParser when accessibility metadata is sparse.

### 2. Local and Replicate backends both sit in the same repeated critical path

The local backend posts screenshots to `/parse/` with the configured timeout:

- `src/mobile_crawler/domain/crawler_agent/tools/omniparser_client.py:252` starts `_parse_local()`.
- `src/mobile_crawler/domain/crawler_agent/tools/omniparser_client.py:277` posts to `/parse/`.

The Replicate backend uses `replicate.Client().run(...)`:

- `src/mobile_crawler/domain/crawler_agent/tools/omniparser_client.py:79` starts `_parse_replicate()`.
- `src/mobile_crawler/domain/crawler_agent/tools/omniparser_client.py:127` calls `client.run(...)`.

Replicate parses are faster in run 107, but the same state-capture callers still trigger repeated parses.

### 3. Reasoning mode uses two LLM phases per step

The crawler is running Manager/Executor reasoning mode. Each step runs:

1. Manager: builds context, captures current UI state, asks the LLM for a plan/subgoal.
2. Executor: asks the LLM which concrete tool action to run.
3. Tool execution: click/type/etc.
4. Wait/verification/recording logic.

Relevant code:

- `src/mobile_crawler/domain/crawler_agent/agent/droid/crawler_agent.py:688` increments and logs the step number.
- `src/mobile_crawler/domain/crawler_agent/agent/droid/crawler_agent.py:691` runs the Manager workflow.
- `src/mobile_crawler/domain/crawler_agent/agent/droid/crawler_agent.py:737` runs the Executor workflow.
- `src/mobile_crawler/domain/crawler_agent/agent/manager/manager_agent.py:423` calls `state_provider.get_state()`.

In run 107, Manager and Executor LLM calls often take 7-16 seconds each, so they remain meaningful even after parser latency is reduced.

### 4. Adaptive wait and verification can trigger extra OmniParser parses

After tool execution, `CrawlerAgentService` wires `UIWaitPredicate` and `ActionVerifier` to the same `state_provider`. In `omniparser` mode, their state reads are also OmniParser parses.

Relevant code:

- `src/mobile_crawler/domain/crawler_agent_service.py:602` sets the crawler's fixed `after_sleep_action` delay to `0.0`.
- `src/mobile_crawler/domain/crawler_agent_service.py:956` captures pre-state through `ActionVerifier.capture_pre_state()`.
- `src/mobile_crawler/domain/crawler_agent_service.py:969` calls `UIWaitPredicate.wait_for_ui_settled()`.
- `src/mobile_crawler/domain/crawler_agent_service.py:988` calls `ActionVerifier.verify()`.
- `src/mobile_crawler/domain/ui_wait_predicate.py:141` polls with `state_provider.get_state()`.
- `src/mobile_crawler/domain/action_verifier.py:73` captures state with `state_provider.get_state()`.

This is useful for correctness, but it is expensive when the state provider is vision-only. A poll that was intended to be cheap becomes another model inference.

### 5. UI dump validation may pay for a parse and then discard it

`CrawlerAgentService` has a UI dump validation path that tries a live `state_provider.get_state()` call, then checks whether the returned object is a `dict`. The current Android state provider returns a `UIState` object, not a dict. That means this path can trigger a full OmniParser parse and then fail to use the result for the live validation branch.

Relevant code:

- `src/mobile_crawler/domain/crawler_agent_service.py:884` comments that it will try `state_provider.get_state()`.
- `src/mobile_crawler/domain/crawler_agent_service.py:889` calls `state_provider.get_state()`.
- `src/mobile_crawler/domain/crawler_agent_service.py:890` checks `isinstance(state, dict)`.

The fallback to `shared_state.a11y_tree` can still work later, but the live parse has already been paid for.

### 6. Finalization captures one more UI state after max steps

After step 5 succeeds, the crawler logs `Reached maximum steps (5)`. It then enters `finalize()` and captures a final screenshot/UI state when vision, screenshot streaming, or trajectory behavior requires it.

Relevant code:

- `src/mobile_crawler/domain/crawler_agent/agent/droid/crawler_agent.py:671` detects max steps.
- `src/mobile_crawler/domain/crawler_agent/agent/droid/crawler_agent.py:852` captures a final screenshot.
- `src/mobile_crawler/domain/crawler_agent/agent/droid/crawler_agent.py:867` calls `state_provider.get_state()` for final UI state.

Run 106 spent about 37 seconds on that final parse. Run 107 spent about 6-7 seconds.

## Screenshot Error Analysis

The Replicate run shows intermittent invalid screenshot errors before several successful parses:

- Step 2: unrecognized PNG stream, then two `open failed` errors for `/data/local/tmp/adbutils-tmp41704.png`.
- Step 3: truncated PNG file, then two `open failed` errors for the same temp path.
- Step 5: broken PNG chunk, then an `open failed` error for the same temp path.

The active screenshot implementation is:

- `src/mobile_crawler/domain/crawler_agent/tools/driver/android.py:219` starts `AndroidDriver.screenshot()`.
- `src/mobile_crawler/domain/crawler_agent/tools/driver/android.py:229` calls `self.device.screenshot_bytes()`.
- `src/mobile_crawler/domain/crawler_agent/tools/driver/android.py:241` verifies the PNG with Pillow.
- `src/mobile_crawler/domain/crawler_agent/tools/driver/android.py:257` logs invalid PNG screenshots.

The repeated fixed remote path `adbutils-tmp41704.png` appears to come from `async_adbutils`, not this repository. The likely failure mode is that `screenshot_bytes()` is using a remote temporary file, and some attempts read a missing, stale, incomplete, or concurrently touched temp file.

## Suggested Fix For The Screenshot Error

Replace or wrap `self.device.screenshot_bytes()` with a crawler-owned screenshot capture method that avoids adbutils' remote temp-file behavior.

Recommended implementation:

1. Add an `asyncio.Lock` on `AndroidDriver` so only one screenshot capture can run at a time per driver instance.
2. Prefer direct stdout capture with `adb exec-out screencap -p` for PNG bytes.
3. Validate the PNG magic bytes and verify with Pillow.
4. If direct stdout capture fails, fall back to a unique remote path such as `/data/local/tmp/mobile-crawler-{pid}-{uuid}.png`, then pull/read it and remove it.
5. On retry, recapture from the device instead of re-reading the same remote temp path.
6. Log screenshot capture duration and whether the capture used `exec-out` or fallback.

Sketch:

```python
class AndroidDriver(DeviceDriver):
    def __init__(self, serial: str | None = None) -> None:
        ...
        self._screenshot_lock = asyncio.Lock()

    async def screenshot(self, hide_overlay: bool = True) -> bytes:
        async with self._screenshot_lock:
            for attempt in range(1, 4):
                try:
                    png = await self._screencap_exec_out()
                    return self._png_to_jpeg(png)
                except Exception as exc:
                    logger.debug("Screenshot attempt %s/3 failed: %s", attempt, exc)
                    await asyncio.sleep(0.2 * attempt)
            raise RuntimeError("Screenshot capture failed after retries")
```

This should remove the repeated `adbutils-tmp41704.png` failures and make screenshot retries more deterministic.

## Most Likely Root Causes Ranked

1. **Vision-only parser mode:** `ui_parser_mode=omniparser` makes OmniParser the primary state source for every step.
2. **Multiple state captures per step:** Manager context, wait/verification, UI dump validation, and finalization can each call `state_provider.get_state()`.
3. **Backend latency:** Local OmniParser is extremely slow in run 106; Replicate is faster but still costs ~5-10 seconds per parse.
4. **Reasoning mode overhead:** Manager plus Executor LLM calls add latency every step.
5. **Screenshot capture instability:** The Replicate run shows retries from invalid/missing screenshots, adding delay and log noise.
6. **No parser result reuse within a step:** The same screen can be parsed more than once by separate runtime layers.

## Recommended Fixes

### Immediate configuration changes

- Switch `ui_parser_mode` from `omniparser` to `boost`.
- Use `accessibility` mode for fast smoke crawls where visual-only controls are not critical.
- Keep OmniParser enabled only as fallback unless the app's accessibility tree is unusable.
- Use Replicate instead of the current local backend when vision-only parsing is required and local inference is CPU-bound.

### Code improvements to consider

- Avoid calling `state_provider.get_state()` inside UI dump validation when `shared_state.a11y_tree` already has current elements.
- Fix the UI dump validation type mismatch so it handles `UIState` objects instead of only `dict`.
- Make `UIWaitPredicate` use a cheaper current-package/accessibility-only probe when parser mode is `omniparser`.
- Reuse the Manager's latest `UIState` for post-action validation when possible instead of reparsing immediately.
- Skip final OmniParser UI-state capture when the run ends only because `max_steps` was reached and no report artifact needs that final parsed state.
- Replace `async_adbutils.device.screenshot_bytes()` with a locked crawler-owned `exec-out screencap -p` screenshot path and unique-path fallback.
- Add explicit timing logs around each `state_provider.get_state()` caller so the AI Monitor can distinguish Manager capture, wait polling, verification, validation, and finalization.

## Practical Expectation

With local OmniParser, a 5-step crawl doing 8-11 parses can reasonably take 5-10 minutes if each parse takes 30-60 seconds. Run 106 matches that behavior.

With Replicate, the same repeated parse pattern can still take about 3 minutes for 5 steps because each parse costs several seconds and the Manager/Executor LLM calls also add per-step latency. Run 107 matches that behavior.

The fastest low-risk change is to run with `ui_parser_mode=boost` and compare the next 5-step crawl. If accessibility data is good for this app, that should remove most of the repeated OmniParser cost regardless of backend.
