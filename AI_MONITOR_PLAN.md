# Wire real data into the AI Monitor panel

## Context

The "AI Monitor" tab (`src/mobile_crawler/ui/widgets/ai_monitor_panel.py`) is a fully built, well-tested widget — per-step list of AI interactions, expandable detail view with screenshot (annotated/OCR toggle), prompt/response JSON trees, parsed actions with reasoning, token/latency metrics, a timing breakdown table, plus status filter and search. It currently shows nothing during real crawls.

Root cause: the widget is correctly wired end-to-end at the UI layer (`main_window.py:366-369` connects `QtSignalAdapter.ai_request_sent/ai_response_received/screenshot_captured` to the panel's `add_request`/`add_response`/`add_screenshot_path` slots), but those signals are only ever emitted by `AIInteractionService` (`src/mobile_crawler/infrastructure/ai_interaction_service.py`) — a class that is **never instantiated anywhere** in the app. It targets a different, unused action/prompt schema and has no relationship to how the real agent actually calls the LLM. The real crawl path (`CrawlerLoop` → `CrawlerAgentService.execute_exploration_task` → `CrawlerAgent` workflow with Manager/Executor/FastAgent/AppOpener sub-agents streaming events) never produces these signals at all. A separate DB table (`ai_interactions`, via `AIInteractionRepository`) already has exactly the right schema for this but is only written twice per run with `step_number` hardcoded to `1`.

Recommended function for the page (confirmed with user): for every step, show what was actually sent to the AI (system/user prompt + screenshot) and what it returned (raw response, parsed action, reasoning, tokens, latency), live during a crawl **and** persisted so past runs can be reviewed later — no rendering changes needed, only real data feeding the existing widget and existing DB table.

## Approach

### 1. Carry prompt/response data out of each LLM call site via existing events

Each sub-agent already builds the full prompt and gets the full response locally, but drops most of it before emitting its event. Add optional fields (no behavior change) to each event class, then populate them where the data is already in scope:

- **Manager** (`agent/manager/events.py` / `manager_agent.py` `get_response`, ~line 527-572): add `system_prompt`, `user_prompt_text`, `screenshot` (bytes) to `ManagerResponseEvent`.
- **Executor** (`agent/executor/events.py` / `executor_agent.py` `get_response`, ~line 150-197): add `prompt_text`, `screenshot` to `ExecutorResponseEvent`. Populate on both the success path and the early-return empty-response path so failures show up too.
- **FastAgent** (`agent/fast_agent/events.py` / `fast_agent.py` `handle_llm_input`, ~line 214-394): add `raw_response`, `prompt_text`, `screenshot`, `fast_agent_llm_ms` to `FastAgentResponseEvent` (no latency is currently timed here at all — add a `time.perf_counter()` wrap around the LLM call like Manager/Executor already do).
- **AppOpener** (`agent/oneflows/app_starter_workflow.py` `AppStarter.open_app_step`, ~line 40-110): currently emits no event at all (runs as its own nested workflow whose stream nobody consumes). Change its `StopEvent.result` from a bare string to a small dict (`success`, `package_name`, `prompt`, `response`, `summary`). Add `workflow_ctx` to `ActionContext` (`agent/action_context.py`), set it at construction in `agent/droid/crawler_agent.py` (~line 504), and in the caller `agent/utils/actions.py:open_app` (~line 189), after unpacking the result dict, emit a new small `AppOpenerResponseEvent` via `ctx.workflow_ctx.write_event_to_stream(...)` — this lands on the outer `CrawlerAgent` handler's stream that the consumer below already iterates, so no new plumbing is needed. Do this now, not as a fast-follow — it's 4 small localized edits.

### 2. Consume the richer events in `crawler_agent_service.py`

`_consume_step_events` (~line 1235-1250) already iterates every workflow event; its `else` branch currently only calls `_buffer_workflow_timing(event)` for timing. Add a sibling call:

```python
else:
    self._buffer_workflow_timing(event)
    await self._handle_ai_interaction_event(event)
```

New `_handle_ai_interaction_event` dispatches on event type (`ManagerResponseEvent` / `ExecutorResponseEvent` / `FastAgentResponseEvent` / `AppOpenerResponseEvent`) into one shared helper that:

- Computes `step_number = self._current_step_number + 1` (the service's step counter only increments in `_handle_tool_execution_event`, *after* these events fire for that step — using `+ 1` uniformly keeps step numbers consistent with what the rest of the UI/DB already show; do not use FastAgent's own internal step counter).
- Builds `request_data = {"user_prompt": json.dumps({...prompt fields..., "screenshot": base64_or_empty})}` — matching the exact shape `ai_monitor_panel.py` already parses (`add_request`/`AIInteractionItem`, lines ~660-682 and ~213-251).
- Builds `response_data = {"response": raw_text, "tokens_input": usage.request_tokens, "tokens_output": usage.response_tokens, "latency_ms": ..., "actions": [...]}`. For Executor, best-effort parse via the existing `parse_executor_response` (`executor/prompts.py`) to populate one action with reasoning; Manager/FastAgent/AppOpener can pass `actions: []` (panel already renders "No parsed actions available" gracefully).
- Writes the step's screenshot to disk once (see §3) and gets a `screenshot_path`.
- Fans out through the callback already threaded into the service (`self._emit_step_phase_event`, set to `CrawlerLoop._emit_event` via `begin_step_tracking(emit_step_phase_event=self._emit_event, ...)`, confirmed at crawler_agent_service.py:169,550,830-832) — call it for `"on_ai_request_sent"`, `"on_ai_response_received"`, `"on_screenshot_captured"`. This reaches the UI live with zero new plumbing, since `_emit_event` already fans out to every registered `CrawlerEventListener` including `QtSignalAdapter`.
- Persists one `AIInteraction` row via `AIInteractionRepository.create_ai_interaction(...)` (schema confirmed: `run_id, step_number, timestamp, request_json, screenshot_path, response_raw, response_parsed_json, tokens_input, tokens_output, latency_ms, success, error_message, retry_count`) with the real per-call `step_number`.

Leave `_log_agent_interaction` (~line 1535-1592) as-is for its existing goal-level start/end bookkeeping row — it's no longer the only source of `ai_interactions` rows, just a distinguishable summary row (no `tokens_input`/`latency_ms`).

### 3. Real screenshot files on disk

Screenshots currently only exist as in-memory bytes (`AndroidDriver.screenshot()`, `tools/driver/android.py:298`) — nothing writes them to disk in the live path, hence `crawler_agent_service.py:1578` hardcoding `screenshot_path=None`. Reuse the existing session-folder convention:

- `crawler_loop.py` (~line 172-175): resolve `screenshots_dir = self.session_folder_manager.get_subfolder(run, "screenshots")` (method already exists, `infrastructure/session_folder_manager.py:153`) and pass into `begin_step_tracking(..., screenshots_dir=screenshots_dir)`.
- `CrawlerAgentService.begin_step_tracking` (~line 535): accept and store `screenshots_dir`.
- In `_handle_ai_interaction_event`, when an event carries screenshot bytes, write once per `(run_id, step_number)` to `screenshots_dir/step_{step_number:04d}.png` (guard with a small `set` to avoid duplicate writes when Manager and Executor both carry the same step's screenshot), then emit `on_screenshot_captured` with that path.

### 4. Retire the orphaned `AIInteractionService`

Delete `src/mobile_crawler/infrastructure/ai_interaction_service.py` and its dedicated test `tests/infrastructure/test_ai_interaction_service.py` — confirmed no other module imports it (`AIInteractionService(` has zero call sites under `src/`), and its action/prompt schema doesn't match the real Executor tool-call format, so there's nothing to port logic-wise (only its `request_data`/`response_data` *shape*, already replicated in §2). Grep once more for `ai_interaction_service` before deleting to catch any stray re-export.

### 5. Files touched

| File | Change |
|---|---|
| `agent/manager/events.py`, `manager_agent.py` | New fields on `ManagerResponseEvent`, populated at `get_response` |
| `agent/executor/events.py`, `executor_agent.py` | New fields on `ExecutorResponseEvent`, populated at `get_response` |
| `agent/fast_agent/events.py`, `fast_agent.py` | New fields on `FastAgentResponseEvent`, add latency timing |
| `agent/oneflows/app_starter_workflow.py` | `StopEvent.result` → dict; new `AppOpenerResponseEvent` |
| `agent/utils/actions.py` (`open_app`) | Unpack dict result, emit `AppOpenerResponseEvent` |
| `agent/action_context.py`, `agent/droid/crawler_agent.py` | Add/set `workflow_ctx` on `ActionContext` |
| `domain/crawler_agent_service.py` | New `_handle_ai_interaction_event`; wire into `_consume_step_events`; `begin_step_tracking` accepts `screenshots_dir`; write screenshot files; emit + persist per-call interactions |
| `core/crawler_loop.py` | Resolve and pass `screenshots_dir` |
| `infrastructure/ai_interaction_service.py` | **Delete** |
| `tests/infrastructure/test_ai_interaction_service.py` | **Delete** |

**Not touched:** `ai_monitor_panel.py`, `signal_adapter.py`, `main_window.py` (wiring already correct), `ai_interaction_repository.py`, `step_phase_models.py`/`step_phase_repository.py` (timing mechanism already works, untouched).

## Verification

- Should pass unmodified: `tests/ui/test_ai_monitor_panel.py` (widget contract unchanged), `tests/infrastructure/test_ai_interaction_repository.py`.
- Add new unit tests for `_handle_ai_interaction_event` per event type: correct `step_number`, correct `request_data`/`response_data` shape, correct emit calls, correct repository call.
- Manual: run a real crawl through the app, confirm the AI Monitor tab populates live per step with prompt text, embedded screenshot, full response, parsed action/reasoning, and timing table; after the run, query `ai_interactions` in the crawler DB and confirm rows with incrementing `step_number` (not all `1`), non-null tokens/latency, and a `screenshot_path` resolving to a real PNG under the run's `screenshots/` folder.
