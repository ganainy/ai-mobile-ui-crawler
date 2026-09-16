# Step-by-Step Mode: Diagnosis & Fix Plan

## TL;DR

Step-by-step mode is **completely non-functional**, not "flaky." The checkbox and
"Next Step" button are fully wired up in the UI, but the backend method they call
(`CrawlerLoop.set_step_by_step_enabled` / `advance_step`) is a stub that does nothing
except print a debug-log line saying the feature "is not supported." Checking the box
never pauses anything, and the run proceeds exactly as if it were unchecked.

This is a **regression from an architecture change**, not a new bug: an older,
fully-working implementation existed and was removed when the crawler was rebuilt
around an internal AI agent, and the UI layer was never updated to match.

---

## 1. How the feature is *supposed* to work (UI layer — intact)

- `crawl_control_panel.py`: `QCheckBox("Step-by-Step Mode")` emits `step_by_step_toggled(bool)`;
  a `next_step_button` ("Next Step" — this is the "Proceed" control) emits `next_step_requested`.
  A `CrawlState.PAUSED_STEP` case makes the button visible/enabled and shows
  "Paused (Step-by-Step)" (`crawl_control_panel.py:151-158`).
- `main_window.py`:
  - `_on_step_by_step_toggled` → `crawler_loop.set_step_by_step_enabled(enabled)` (`main_window.py:806-810`), persists the preference to `user_config_store`.
  - `_on_next_step_requested` → `crawler_loop.advance_step()` (`main_window.py:816-819`).
  - State-change events from the loop are turned into `CrawlState` and pushed to `control_panel.update_state(...)` (`main_window.py:991-993`), which is what would reveal the "Next Step" button.

All of this is real, working code. **The break is entirely below this layer.**

## 2. Where it actually breaks (backend — stubbed out)

`src/mobile_crawler/core/crawler_loop.py` is the only `CrawlerLoop` implementation in the
codebase (confirmed — no legacy/alternate loop class exists). Its control methods are no-ops:

```python
def set_step_by_step_enabled(self, enabled: bool) -> None:
    self._emit_event("on_debug_log", ..., "Step-by-step mode not supported in internalized crawler mode.")

def is_step_by_step_enabled(self) -> bool:
    return False

def advance_step(self) -> None:
    self._emit_event("on_debug_log", ..., "Advance step not supported in internalized crawler mode.")
```
(`crawler_loop.py:119-139`). `pause()`/`resume()` are the same shape — also stubbed.

`CrawlerLoop.run()` tracks state as a bare string (`self._state`, values `RUNNING`/`ERROR`/`STOPPED`
— `crawler_loop.py:63,464-469`), which **never becomes `PAUSED_STEP`**. So even independent of the
stub, the UI's `CrawlState.PAUSED_STEP` branch can never be reached — the "Next Step" button can
never appear.

The actual exploration work happens in one continuous call:
`self._crawler_agent_service.execute_exploration_task(...)` (`crawler_loop.py:246`), which hands
control to an internal `CrawlerAgent` workflow (`crawler_agent_service.py:1441-1446`, a
`llama-index`-style `@step`/`Context`/event workflow under
`domain/crawler_agent/agent/droid/crawler_agent.py`). That agent runs its own steps
(`run_manager` → `run_executor` → `handle_executor_result` → ...) autonomously; `CrawlerAgentService`
only *observes* its event stream for timing/telemetry (`_consume_step_events`,
`crawler_agent_service.py:1463-1477`) — it has no hook to pause the agent between steps.

### Corroborating evidence this is a known/accepted gap, not an intermittent bug

- `tests/core/test_crawler_loop.py:646-658` literally asserts the stub behavior is correct:
  `test_set_step_by_step_enabled_emits_debug_log`, `test_advance_step_emits_debug_log`,
  `test_is_step_by_step_enabled_returns_false`. The test suite passing gives false confidence.
- Git history (`git log -p -- src/mobile_crawler/core/crawler_loop.py`) shows a **prior working
  implementation** at commit `60716b5...` and earlier: real per-step `threading.Event`
  (`_step_advance_event`), a `CrawlStateMachine` with `PAUSED_STEP`, and a manual Python
  `while self._should_continue(...)` loop that called `_execute_step()` once per iteration and
  blocked on the event before continuing. This was removed when the crawler was rewired to
  delegate to the internal AI agent (commit history around "Integrate DroidRun AI agent system" /
  "Add crawler agent timing and UI diagnostics"), and the pause/step methods were replaced with
  "not supported" stubs — but the checkbox, button, and persisted setting were left in the UI.
- `CrawlStateMachine` (`crawl_state_machine.py`, with `PAUSED_STEP`) is now dead code — it is
  instantiated nowhere except its own unit test (`tests/core/test_crawl_state_machine.py`).

### A confusing extra wrinkle: the "Enable Crawler Agent" checkbox

`main_window.py:455-463` disables step-by-step/pause when Settings → "Enable Crawler Agent" is
checked, and re-enables their *availability* when it's unchecked — implying unchecking it should
restore working step-by-step mode. **It does not.** `CrawlerLoop.run()` never reads
`enable_crawler_agent` at all (confirmed by grep — zero references in `crawler_loop.py`); it always
builds a `CrawlerAgentService` and always calls `execute_exploration_task`. So unchecking that box
just re-enables a checkbox that still does nothing — an extra layer of false affordance on top of
the first one.

## 3. Why you're seeing "not working" and not a crash

Nothing throws. The checkbox toggles happily, the preference persists across restarts, and a debug
log line quietly says the feature isn't supported (easy to miss among other debug output). The run
just executes start-to-finish with no pauses, which reads as "step-by-step mode doesn't do anything"
— which is exactly what's happening.

## 4. What a real fix requires

The old approach (a manual Python loop calling `_execute_step()` once per iteration) no longer
exists — steps now happen inside the agent's own workflow, so the fix has to plug into that
workflow rather than resurrect the old loop. Two viable strategies:

**Option A — pause inside the agent workflow (true per-step pause, more invasive)**
Add a workflow step (or a check inside `handle_executor_result`, after each action completes and
before the next `run_manager` decision) that, when step-by-step mode is enabled, awaits an
external "advance" event via the workflow's `Context` (e.g. `ctx.wait_for_event(StepAdvanceEvent)`,
the same human-in-the-loop pattern these workflow libraries support). `CrawlerLoop.advance_step()`
would send that event into the running `WorkflowHandler`'s context
(`handler.ctx.send_event(StepAdvanceEvent())`). This gives a real pause between each
decide/execute cycle, matching the original UX intent (see the goal in your message: run one
step, wait for Proceed, run the next).

**Option B — pause in the event-consumer only (simpler, weaker guarantee)**
Have `_consume_step_events` block on an `asyncio.Event` after each `ToolExecutionEvent` before
processing further events, and update UI/telemetry state to `PAUSED_STEP`. This is much less
invasive but does **not** actually stop the agent from continuing to act during the pause — it only
delays *observation* of what already happened, so debugging still shows the agent racing ahead.
This does not deliver what you asked for (pause execution, not just pause reporting), so it's
listed only as a fallback if Option A proves impractical.

Given your stated goal — genuinely stopping after each step so you can inspect it before
continuing — **Option A is the one that actually satisfies the requirement**; Option B would look
like it works but wouldn't actually gate execution.

Either option needs:
1. Restoring a real `PAUSED_STEP`-equivalent state that reaches `main_window.py` → `control_panel.update_state(...)`, since `CrawlerLoop._state` today only knows `RUNNING/ERROR/STOPPED`.
2. Rewriting the now-misleading tests in `tests/core/test_crawler_loop.py:646-658` to assert real pause/advance behavior instead of asserting the stub.
3. Deciding what to do with the "Enable Crawler Agent" gating in `main_window.py:455-463` / `:1322-1323`, since there is only one code path now — either remove the false gating or make it mean something real again.

## 5. Open questions before implementing

- Is Option A (true pause inside the agent's `Context`/event workflow) acceptable, given it touches the agent workflow internals (`domain/crawler_agent/agent/droid/crawler_agent.py`) rather than just `CrawlerLoop`?
- Should "Next Step" advance exactly one *tool execution* (one action), or one full decide→execute *agent cycle* (which may include multiple internal AI calls)? This affects where the pause point is inserted.
- Should the pause also freeze traffic capture / video recording timers, or let them keep running during the paused interval?
- What should happen to the "Enable Crawler Agent" checkbox and its step-by-step gating once there's only one execution path — remove it, or repurpose it?
