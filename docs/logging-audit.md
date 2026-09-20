---
author: claude
created: 2026-09-20
status: partly applied 2026-09-20 (see "Applied" at the end)
---
# Logging audit

Scope: every `logger.*` call under `src/mobile_crawler` (~800 calls: 248 debug, 174 info, 223 warning, 151 error, 1 exception). Not reviewed in detail: `crawler_agent/macro/` (57 calls, replay + CLI), `telemetry/` (29), `mcp/` (7), `credential_manager/` (9). Proposed to stay as is.

Level contract used below: ERROR = a step/run/feature failed; WARNING = degraded but continuing; INFO = a milestone the user would narrate (one line per step/action, not per internal call); DEBUG = internals (ADB, HTTP, payloads, timings, prompt/response bodies).

## A. Root cause: the plumbing, not the call sites

| # | Finding | Where | Proposed fix |
|---|---------|-------|--------------|
| A1 | Every record from the `crawler_agent` logger (ERROR/WARNING/INFO included) reaches the GUI as **DEBUG**. `CrawlerLogHandler.emit` forwards only the message text through `on_debug_log`; `MainWindow._on_debug_log` hardcodes `LogLevel.DEBUG`. `crawler_agent` has `propagate=False` during a run, so the root `QLogHandler` (which does keep levels) never sees them. This is why the viewer level filter looks useless. | `crawler_agent_service.py:105-123, 400-402`, `main_window.py:993-995` | Carry the record's level through the event (`on_debug_log(run_id, step, message, level)`), map it in `_on_debug_log`. |
| A2 | `log_level` setting exists (`defaults.py:18`) but nothing reads it. | `config/defaults.py` | Wire to UI/CLI handler thresholds; add `--log-level` to `crawl`. Files stay at DEBUG. |
| A3 | Root logger forced to DEBUG, `crawler_agent` forced to DEBUG per run. Correct for files; combined with A1 it means the GUI gets everything as DEBUG. The child names set at `:396` (`crawler_agent.agent/.tools/.config_manager`) are dead: all modules log to plain `crawler_agent`. | `main_window.py:1668-1679`, `crawler_agent_service.py:396-398` | Keep DEBUG at logger level; set threshold on the handlers. Drop the dead child names. |
| A4 | Captured stdout/stderr lines are all pushed as DEBUG. | `log_sinks.py:255-265` | Keep DEBUG (they are unstructured); verify what still prints outside logging. |
| A5 | **Live stats are mined from log text** (`_parse_droidrun_progress`: `Step N/M`, `... response:`, `✅/❌ Execution complete:`, `<name>`, `<output>`, `<error>`). Reworded or removed messages silently break the counters. | `main_window.py:1000-1090` | Treat these messages as a frozen contract; add a comment at each emitter; parsing must stay before any level filtering. |
| A6 | LLM bodies and tokens at INFO: streamed deltas one record per token (`inference.py:101,205`), full response text (`inference.py:59,161,257`), tool-result XML (`fast_agent.py:537-538`). | `agent/utils/inference.py`, `fast_agent.py` | DEBUG (keep the `... response:` header lines at INFO because of A5). |

## B. Level changes

| File:line | Now | Proposed | Why |
|-----------|-----|----------|-----|
| `inference.py:59,101,104,161,205,208,257` | INFO | DEBUG | response bodies / per-token stream (A6) |
| `fast_agent.py:537-538` | INFO | DEBUG | tool result XML dump |
| `executor_agent.py:273` | DEBUG | INFO | the per-action line ("Executing action: ...") |
| `executor_agent.py:309` | DEBUG | INFO | action result; mined by A5 |
| `crawler_agent.py:709` | DEBUG | INFO | Manager's subgoal per step |
| `tools/ui/provider.py:257,274` | INFO | DEBUG | "Using OmniParser only/boost (N elements)" every step; the timing INFO already covers it |
| `state_graph.py:131` | DEBUG | keep DEBUG | duplicate of `screen_tracker.py:160` (INFO) |
| `database.py:434` | WARNING | DEBUG | "migration step skipped (may already exist)" is expected on every start |
| `portal_client.py:195,199` | WARNING | WARNING once per run | degraded, but fires on every call today |
| `mobsf_manager.py:808` | INFO | DEBUG (or throttle) | poll-progress line every tick |
| `mobsf_manager.py:455,463,569,600` | INFO | keep one per artifact | fine, milestones |
| `stale_run_cleaner.py:88,107,109,129` | INFO | DEBUG | four lines per run for one milestone (`:51` and `:56` stay INFO) |
| `providers/registry.py:384,412,420`, `vision_detector.py:62` | INFO | DEBUG | model-cache housekeeping |
| `providers/registry.py:99,163,207` | ERROR | WARNING | model list fetch failure is survivable |
| `adb_client.py:76,79,82` | ERROR | WARNING (79 stays ERROR) | timeouts in polling paths |
| `traffic_capture_manager.py:193,252` | INFO | DEBUG | argument dumps and resolved-activity detail |
| `ui_context.py:43` | INFO | keep INFO | A11y issues are research output; flag for your call |

## C. Delete / merge duplicates

- **`[DEBUG]` prefix** on ~35 messages in `traffic_capture_manager.py`: delete the prefix (level already says it).
- **Same event logged 2-3 times** across layers. Rule: the lowest layer raises or logs DEBUG, the layer that handles it logs once.
  - "Saved run_stats": `runtime_stats_collector.py:657` (INFO), `run_stats_repository.py:54` (DEBUG), `main_window.py:970` (INFO) -> keep one INFO.
  - "MobSF analysis failed": `mobsf_manager.py:702,714,733` (ERROR each) + `:213-224` request errors + `crawler_loop.py:547` (WARNING) -> one at the boundary.
  - "Failed to fetch Gemini/OpenRouter/Ollama models": `registry.py` (ERROR) and `vision_detector.py` (WARNING).
  - "OmniParser client initialized": `crawler_agent_service.py:562` and `tools/omniparser_client.py:502`; Replicate/local errors duplicated between `domain/omni_parser_client.py` and `tools/omniparser_client.py`.
  - "Max duration ... reached": identical message at `crawler_agent_service.py:1610` and `:1629`.
  - "Accessibility service enabled": `portal.py:439` and `:587`.
  - "Trajectory folder" (`trajectory.py:40`) vs "Trajectory saved" (`crawler_agent.py:896`).
  - Device disconnected / execution error: `crawler_agent.py:617,625,636,679` log the same failure up to three times.
- **Debug chatter to delete**: `tools/omniparser_client.py:170,184,191,200,215,216,285` (image header bytes, temp file, raw output), `llm_picker.py:67-100` (collapse import steps into one line), `portal_client.py` `✓ TCP mode` style duplicates.

## D. Tracebacks

151 ERROR calls, only 1 `logger.exception`, and `crawler_agent.py:627,638,858` emit `logger.error(traceback.format_exc())` as a second record. Proposed: unexpected exceptions get `exc_info=True` on the single ERROR record; expected failures (timeouts, unreachable server, optional dependency missing) get none.

## E. Logs to add

1. **Per-step summary** (INFO), one line at the end of each step: `Step N/M | screen (new/seen) | action | ok/fail | duration | tokens`. Today these facts are spread over 4-5 lines and DEBUG records.
2. **Run banner** (INFO): app, device, model(s), parser mode, `max_steps`, `max_actions_per_batch`, log file location. **Run summary** (INFO): steps, actions ok/failed, screens discovered, tokens, duration. (Check `crawler_agent_service.py:699,1716` first; some of this may exist.)
3. **Action Batch**: INFO with number of actions executed in the batch (only the abort case is logged now, `executor_agent.py:316`).
4. **LLM call**: one line per call (agent, model, latency, tokens) at DEBUG.
5. **Active log level and log file path** at startup (INFO).

## F. Cosmetic / out of scope

- 795 calls are mostly f-strings, not lazy `%s`. Skipped: cost is negligible here.
- Emojis in messages stay (A5 regexes depend on `✅`/`❌`).
- Two logger namespaces (`crawler_agent` vs `__name__`). Left alone.

## Applied (2026-09-20)

Done, full suite green (`tests/`, integration excluded):
- **A1**: `on_debug_log(run_id, step, message, level="INFO")` carries the record level (listener ABC, `SignalAdapter`, CLI listener, `MainWindow._on_debug_log`, `CrawlerLogHandler`). Loop failure events pass `"WARNING"`, captured stdout/stderr pass `"DEBUG"`, the `UI: ...` settings dumps pass `"DEBUG"`. `CrawlerLogHandler` now appends the traceback when a record has `exc_info`.
- **A2**: `--log-level` on `crawl` (default: the `log_level` setting, INFO) filters the JSON `debug_log` events. The GUI viewer now starts at INFO (entries are buffered, so DEBUG is one filter click away). There is no Settings widget.
- **A5**: comments added at the `Step N/M` and `Execution complete` emitters.
- **A6 / B**: LLM bodies, token stream and tool-result XML -> DEBUG; per-action lines (`Executing action`, `Execution complete`, `Proceeding to Executor`) -> INFO; OmniParser-source, MobSF poll/request-layer, stale-run cleanup, model-cache and `start_capture_async` lines -> DEBUG; model-fetch failures and ADB timeout/exception -> WARNING; schema-migration skip -> DEBUG.
- **C**: `[DEBUG]` prefix stripped from `traffic_capture_manager.py`; "Saved runtime stats" INFO in the collector -> DEBUG (the UI one stays); MobSF request-layer errors -> DEBUG (callers report once).
- **D**: three `logger.error(traceback.format_exc())` pairs in `crawler_agent.py` merged into `exc_info=True`.
- **E1/E2**: `Step N: tool=... success=... in Nms` is now INFO (the per-step line); run banner (`Run N starting: package, model, parser, max_steps, actions_per_batch, max_duration_s`) added. The run summary already existed (`Crawler agent completed: ...`).

Not done / corrected:
- The "Max duration reached" and "Accessibility service enabled" pairs are different code paths, not duplicates. Left as is.
- Not done: E3 (batch size line), E4 (per-LLM-call line), E5 (log path at startup), warn-once for `portal_client` TCP fallback, the duplicated OmniParser init/error messages, the dead `crawler_agent.*` child logger names (A3), `ui_context.py:43` kept at INFO by decision.
- Not exercised in the real GUI or on a device.
