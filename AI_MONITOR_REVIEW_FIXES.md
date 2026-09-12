# AI Monitor implementation — code review fixes

Findings from `/code-review` on the uncommitted implementation of `AI_MONITOR_PLAN.md`. This document describes how to fix each one; nothing here has been applied yet.

## 1. AppStarter hardcodes `success=True` even when the driver failed

**File:** `src/mobile_crawler/domain/crawler_agent/agent/oneflows/app_starter_workflow.py:122-133`

`driver.start_app()` can return a **string describing failure** instead of raising (`AndroidDriver.start_app()` returns `f"Failed to start app {package}: {e}"`; `IosDriver` returns a similar `"Failed to launch ..."` string on non-200). `open_app_step` wraps whatever comes back into `{"success": True, "summary": result}` unconditionally, so a real device failure is reported as a success.

**Fix:** reuse the existing check already used two call sites over in `actions.py` (`open_app`/`open_bundle_id`, lines 179 and 244: `result.lower().startswith("failed")`):

```python
result = await self.driver.start_app(package_name)
failed = isinstance(result, str) and result.lower().startswith("failed")
summary = result if isinstance(result, str) else f"Started {package_name}"

return StopEvent(
    result={
        "success": not failed,
        "package_name": package_name,
        "prompt": prompt,
        "response": response_text,
        "summary": summary,
    }
)
```

## 2. `response_data` never carries a success/error signal

**File:** `src/mobile_crawler/domain/crawler_agent_service.py:1181-1187` (`_handle_ai_interaction_event`)

`ai_monitor_panel.py`'s `_determine_success()` (line 767) looks for `response_data["success"]` (bool), then `error_message`, then a `parsed_response`/`actions_count` fallback. The dict built here only ever has `{response, tokens_input, tokens_output, latency_ms, actions}` — none of those keys match, so every interaction falls through to `return False` and renders with a red ✗ regardless of outcome.

**Root fix:** give each response event class an explicit outcome, the same way `AppOpenerResponseEvent` already does (`success: bool`), instead of inferring it downstream:

- `ManagerResponseEvent`, `ExecutorResponseEvent`, `FastAgentResponseEvent` (their `events.py` files): add `success: bool = True` and `error: str | None = None`.
- `executor_agent.py`'s `ValueError` fallback branch (lines 171-186, "Executor failed to respond, try again") should construct its event with `success=False, error=str(e)` instead of leaving it implicit.
- Manager and FastAgent currently have no equivalent per-call failure branch that reaches their `ResponseEvent` (real failures raise/short-circuit before the event is built), so `success` simply stays at its `True` default there — no extra branching needed for them right now.

Then in `_handle_ai_interaction_event`, read it straight off the event instead of guessing:

```python
success = getattr(event, "success", True)
error_message = getattr(event, "error", None)
...
response_data = {
    "response": raw_response or "",
    "success": success,
    "error_message": error_message,
    "tokens_input": tokens_input,
    "tokens_output": tokens_output,
    "latency_ms": latency_ms,
    "actions": actions,
}
```

For `AppOpenerResponseEvent`, `event.success` is already populated correctly by `actions.py:205` — just wire it through the same way instead of the current `usage = None; latency_ms = None` branch that drops it.

## 3. Persisted `AIInteraction` rows hardcode `success=True, error_message=None`

**File:** `src/mobile_crawler/domain/crawler_agent_service.py:1214-1215`

Same root cause as #2 — once that fix lands, reuse the same `success`/`error_message` values here instead of the literals:

```python
interaction = AIInteraction(
    ...
    success=success,
    error_message=error_message,
    ...
)
```

Without this, reviewing a past run's `ai_interactions` rows can't tell a failed AI call from a successful one — the exact "review past runs" goal `AI_MONITOR_PLAN.md` was written to support.

## 4. `add_request()` orphans/overwrites rows when a step has multiple AI calls — and the list should show one merged row per step, not one per call

**File:** `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` — `_interactions` dict, `add_request` (~line 570), `_add_list_item` (~line 633), `add_response`/`_update_list_item` (~line 603, 792)

The panel's data model assumes **one AI call per step** (`self._interactions` keyed by `step_number`, one `_list_item`/`_item_widget` per key). The new producer emits `on_ai_request_sent`/`on_ai_response_received` **once per sub-agent** (Manager, then Executor, sometimes FastAgent) for the *same* `step_number`. Today:
- `add_request` always calls `_add_list_item(step_number, pending=True)`, which unconditionally appends a new `QListWidgetItem` — it never checks whether a list item already exists for that step. The Manager's item becomes orphaned (still visible in the list) the moment the Executor's `add_request` fires for the same step.
- Both calls write into the *same* `self._interactions[step_number]` dict, so the Executor's `request_data`/`response_data` silently overwrite the Manager's — the Manager's `system_prompt`/`user_prompt` is gone from what's ultimately displayed.

**Confirmed direction (2026-09-13): the list should show exactly one row per crawl step**, not one row per AI call — screenshots of the running panel showed "Step 1" twice back to back, which reads as a bug/duplicate even once the data itself is correct. Internally, though, each call's data still needs its own slot so nothing gets overwritten. Two-layer fix:

**Layer 1 — stop overwriting, key each call separately internally:**

1. Add a monotonically increasing counter, e.g. `self._call_seq = 0`, and an ordering structure `self._calls_by_step: dict[int, list[str]] = {}`.
2. In `add_request(run_id, step_number, request_data)`: generate `call_key = f"{step_number}:{self._call_seq}"`, increment the counter, store the call under `self._calls[call_key]` (a new dict, separate from the step-level list-row bookkeeping), and append `call_key` to `self._calls_by_step.setdefault(step_number, [])`.
3. In `add_response(run_id, step_number, response_data)`: pop/peek the **oldest still-unanswered** `call_key` for that `step_number` and update `self._calls[call_key]` — safe because the producer emits request→response synchronously per call, in order, before moving to the next sub-agent's call.
4. `add_screenshot_path(run_id, step_number, screenshot_path)` stays keyed by `step_number` alone in its own small dict (`self._screenshot_paths`) — it's one device screenshot per crawl step, not per AI call.

**Layer 2 — render one aggregated row per step, not one per call:**

5. Keep a separate `self._interactions: dict[int, dict]` keyed by `step_number` for what the **list row** displays — `_add_list_item`/`_update_list_item` operate on this, not on individual calls.
6. On every `add_response`, after updating `self._calls[call_key]`, recompute the step's aggregated summary: preview text should reflect the **most recent call with an actual action** (i.e. prefer the Executor's/FastAgent's parsed action over the Manager's plan-only response when both exist for the step — the Manager call rarely has a `parsed_actions` entry, so "last call with `actions`" is a simple, correct rule), and overall `success` for the row should be the logical AND of all calls made so far for that step (any failed call marks the step's row as failed, since "the AI acted" implies every call in the chain succeeded).
7. Only call `_add_list_item` (append) on the **first** call seen for a `step_number`; every subsequent call for the same step goes through `_update_list_item`'s existing remove-and-replace path instead, driven off the recomputed aggregate summary from step 6 — this is what actually eliminates the duplicate "Step 1" rows.
8. `_on_show_details` (Show Details button) should look up `self._calls_by_step[step_number]` and pass **all** calls for that step to the detail dialog, in order, instead of a single request/response pair — see §9 below for how the dialog presents multiple calls.

**Backward compatibility:** `tests/ui/test_ai_monitor_panel.py` calls `add_request` then `add_response` exactly once per step — with exactly one call in the step's chain, steps 6-7 degrade to the current single-row behavior, so no test changes should be needed for the existing single-call case. Add new tests specifically for the multi-call-per-step case (2+ calls, one row, correct aggregate success, `Show Details` surfacing both calls).

## 5. `step_number = self._current_step_number + 1` can collide after a mid-cycle exception

**File:** `src/mobile_crawler/domain/crawler_agent_service.py:1107`

`self._current_step_number` only advances inside `_handle_tool_execution_event`, which fires *after* the AI response events for that step. If an exception happens between the executor's response and the tool actually executing (so `ToolExecutionEvent` is never emitted for that cycle), the counter never advances — the next real decide/execute cycle computes the *same* `step_number` again. That collides with the screenshot dedup guard (`self._screenshot_written`, line ~1159 — the second cycle's screenshot silently isn't written because the key looks "already done") and makes two distinct AI calls share one `ai_interactions.step_number`.

**Fix:** don't derive the AI-interaction step number from a counter that a downstream, possibly-skipped event increments. Options, in order of preference:
- **Increment a dedicated counter for AI-call numbering directly in `_handle_ai_interaction_event`** (e.g. `self._ai_call_step_number`) whenever a *new decide cycle* starts (i.e., on the first event of a cycle — a `ManagerResponseEvent`/`ExecutorContextEvent` boundary), rather than reusing `_current_step_number + 1`. This makes AI-call numbering self-contained and immune to whether the tool-execution step later succeeds, fails, or throws.
- If step numbers must stay perfectly aligned with `_current_step_number` (used elsewhere for DB/UI consistency), instead make `_handle_tool_execution_event` robust to a skipped/failed cycle — e.g. advance the counter in a `finally`/exception handler around the tool-execution path too, so it always advances exactly once per decide/execute cycle regardless of outcome.

Either way, add a regression test that simulates an exception between `ExecutorResponseEvent` and `ToolExecutionEvent` and asserts the next cycle gets a distinct step number.

## 6. Redundant local `import os`

**File:** `src/mobile_crawler/domain/crawler_agent_service.py:1160`

`os` is already imported at module scope (line 6). Delete the local `import os` inside `_handle_ai_interaction_event` — purely a cleanup, no behavior change.

## 7. Five imports run on every non-tool workflow event

**File:** `src/mobile_crawler/domain/crawler_agent_service.py:1094-1098`

`_handle_ai_interaction_event` is called for *every* event that isn't a `ToolExecutionEvent` (per `_consume_step_events`'s `else` branch), and the first thing it does is import 4 event classes + `parse_executor_response`, before the `isinstance` check on line 1100 discards most of them (`ScreenshotEvent`, `RecordUIStateEvent`, `ManagerContextEvent`, etc. all pay this cost and do nothing with it).

**Fix:** move those 5 imports to module level in `crawler_agent_service.py` (they were presumably kept local only to dodge a circular-import concern — verify there isn't one; if there is, hoist them into a single lazy import guarded by a module-level flag/cache instead of repeating it on every event).

## 8. Executor's response is parsed twice per step

**File:** `src/mobile_crawler/domain/crawler_agent_service.py:1132-1133` vs. `executor_agent.py`'s `process_response` step

The Executor's raw `### Thought/### Action/### Description` response text is parsed once by `ExecutorAgent.process_response` to build the real action, and parsed **again** here via `parse_executor_response(raw_response)` purely to populate the monitor's `actions` field — duplicate CPU work every step, and a risk that the two call sites' parsing behavior drifts apart if one is changed without the other.

**Fix:** don't re-parse. Have `ExecutorAgent` attach its already-parsed result onto `ExecutorResponseEvent` when it emits it (e.g. add `parsed_action: dict | None = None` to the event, set it right after `process_response` parses the response), and in `_handle_ai_interaction_event` read `event.parsed_action` directly instead of calling `parse_executor_response` a second time. Keep the existing `try/except` around building the `actions` list in case `parsed_action` is `None` on an early-failure path.

## 9. Step Details dialog: result-first layout, multi-call aware

**File:** `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` — `StepDetailWidget._setup_ui` (~line 190-415)

User feedback on the current layout (screenshot, 2026-09-13): everything is crammed onto one screen with no priority — Screenshot + Prompt Data share the top row (prime real estate) while Response + Parsed Actions, which the user considers **more important than the input**, are pushed to the bottom, below a full-width Timing Breakdown table. It reads as cluttered rather than organized.

**Confirmed direction: "result-first stack".** Reorganize `StepDetailWidget` into two tiers:

**Top tier (always visible, no scrolling to reach it) — the result:**
- Left: Screenshot group, unchanged (Annotated/OCR toggle stays as-is).
- Right: a new "Result" group that merges what's currently the separate `Response` and `Parsed Actions` groups into one prioritized view — parsed action + reasoning shown first and prominently (this is "what the AI decided to do"), with the full raw response text available underneath via a collapsed/expandable sub-section (e.g. a `QToolButton` with `Qt.ToolButtonStyle` "checkable" arrow, or a nested `QGroupBox` that starts collapsed) rather than a separate always-open tree.
- If §4/§8 lands first (multiple calls per step), this tier needs a small selector for which call's result is showing — e.g. a row of small tabs/buttons above the Result group: "Manager (plan)" / "Executor (action)", defaulting to the last call with an actual parsed action (same rule as the list-row preview in §4.6), since that's the one the user actually cares about first.

**Bottom tier (collapsed by default, one click to expand) — supporting detail:**
- "Prompt sent" — the current `Prompt Data` `JsonTreeWidget`, moved here, collapsed by default (it's the least important thing to a user checking "what did the AI do", per their own framing).
- "Timing breakdown" — the current table, moved here, collapsed by default (diagnostic/perf info, not part of the primary story).

Use a consistent collapsible-section widget for both (a small reusable `CollapsibleGroupBox` wrapping the existing `QGroupBox`/table works — Qt doesn't have one built in, but it's a small wrapper: a checkable header button that toggles the content widget's visibility). Reuse it for both sections rather than building two different collapse mechanisms.

**Not changing:** the underlying data (`JsonTreeWidget` for prompt, the timing table construction, the screenshot toggle logic) — this is a layout/prioritization change only, per the user's framing ("I don't like how it looks", not "the data is wrong").

## Suggested fix order

1 → 2 → 3 (single root cause chain: event-level success signal, consumed by both the live panel and the DB row) should land together as one change, since #3 depends on #2's fix.
4 and 5 are independent structural fixes to the panel's data model and the step-numbering respectively — do them next, each with its own test.
9 (detail-dialog redesign) depends on §4's per-step call list (`self._calls_by_step`) to know what to show in the call selector — do it right after 4.
6, 7, 8 are safe, isolated cleanups — do these last, in one small pass.
