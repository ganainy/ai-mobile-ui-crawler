# Handover: wire `CrawlStateMachine` validation + fix `StepPhaseStateMachine.get_phase_duration`

Two independent, unrelated bugs bundled into one handover since they were flagged together
during a `/code-review` of the step-by-step mode feature (see
`specs/step-by-step-mode-fix-plan.md`). Both were deliberately deferred at the time — this
doc has the investigation already done; the next agent just needs to implement and verify.

---

## Part 1 — `CrawlStateMachine` isn't wired into `CrawlerLoop`

### Current state

`src/mobile_crawler/core/crawl_state_machine.py` defines `CrawlStateMachine`, a real state
machine with transition validation (`transition_to()` raises `ValueError` on an invalid
transition per the matrix in `_is_valid_transition()`, lines 74-83). It is **fully unused** —
grep confirms it's only ever instantiated in `tests/core/test_crawl_state_machine.py`.

`CrawlerLoop` (`src/mobile_crawler/core/crawler_loop.py`) tracks state as a **plain string**
(`self._state`), only borrowing `CrawlState` for its `.value` constants:

```
src/mobile_crawler/core/crawler_loop.py:64   self._state = CrawlState.UNINITIALIZED.value
src/mobile_crawler/core/crawler_loop.py:157  if self._state != CrawlState.PAUSED_STEP.value:
src/mobile_crawler/core/crawler_loop.py:177  self._transition_state(CrawlState.RUNNING.value, ...)   # advance_step()
src/mobile_crawler/core/crawler_loop.py:213  self._transition_state(CrawlState.RUNNING.value, run_id) # run() start
src/mobile_crawler/core/crawler_loop.py:226  emit_state_change=lambda state: self._transition_state(state, run_id)  # -> "paused_step" from CrawlerAgentService
src/mobile_crawler/core/crawler_loop.py:443  self._transition_state(CrawlState.ERROR.value, run_id)   # except CrawlerError
src/mobile_crawler/core/crawler_loop.py:452  self._transition_state(CrawlState.ERROR.value, run_id)   # except Exception
src/mobile_crawler/core/crawler_loop.py:460  self._transition_state(CrawlState.STOPPED.value, run_id) # finally block
src/mobile_crawler/core/crawler_loop.py:517  def _transition_state(self, new_state, run_id): self._state = new_state; ...
```

`_transition_state()` (line 517) does a raw assignment with no validation at all. A code
review flagged this as a lost safety net: nothing stops an invalid sequence (e.g. two racing
async callbacks producing `paused_step -> stopped -> running`) from being silently accepted.

### Why it wasn't just wired in

`CrawlStateMachine`'s matrix (`crawl_state_machine.py:74-83`) requires an intermediate
`STOPPING` state before `STOPPED`:

```python
CrawlState.RUNNING: [CrawlState.PAUSED_MANUAL, CrawlState.PAUSED_STEP, CrawlState.STOPPING, CrawlState.ERROR],
CrawlState.ERROR: set(),  # terminal — no valid targets at all
```

But `crawler_loop.py`'s `run()` **never sets `STOPPING`** anywhere. Its `finally` block
(line 454-460) unconditionally transitions straight to `STOPPED`:

- **Happy path**: state is `RUNNING` the whole time; `finally` calls `STOPPED` directly →
  `RUNNING -> STOPPED`, not a valid edge in the matrix.
- **Error path**: the `except` blocks (443, 452) already set `ERROR` before `finally` runs →
  `ERROR -> STOPPED`, and `ERROR` is terminal (no valid targets at all) in the matrix.

Naively swapping `_transition_state` to call `CrawlStateMachine.transition_to()` would raise
`ValueError` in the cleanup path of **every single run** — not an edge case, the common case.
That's why this was left alone rather than done as a drive-by fix during the step-by-step
review.

### Recommended fix

Two decisions to make, in order:

1. **Fix the matrix to match reality**, since `crawler_loop.py` genuinely has no separate
   "stopping" phase today (cancellation just sets `self._cancel_requested = True` and the
   same `finally` block runs either way). Add direct edges instead of inventing a
   `STOPPING` phase that nothing would ever actually enter:
   ```python
   CrawlState.RUNNING: [CrawlState.PAUSED_MANUAL, CrawlState.PAUSED_STEP, CrawlState.STOPPING, CrawlState.STOPPED, CrawlState.ERROR],
   CrawlState.PAUSED_STEP: [CrawlState.RUNNING, CrawlState.PAUSED_MANUAL, CrawlState.STOPPING, CrawlState.STOPPED, CrawlState.ERROR],
   CrawlState.PAUSED_MANUAL: [CrawlState.RUNNING, CrawlState.STOPPING, CrawlState.STOPPED, CrawlState.ERROR],
   CrawlState.ERROR: [CrawlState.STOPPED],  # was terminal; finally always drives ERROR -> STOPPED
   ```
   Update `tests/core/test_crawl_state_machine.py` for the new allowed edges (check it doesn't
   assert `RUNNING -> STOPPED` or `ERROR -> STOPPED` are currently invalid — if it does,
   that assertion needs to change too).

2. **Wire `CrawlerLoop._transition_state()` through the state machine, but don't let a matrix
   gap crash a live run.** Give `CrawlerLoop` a `CrawlStateMachine` instance, drive
   `self._state` from it, and catch `ValueError` around the transition rather than letting it
   propagate — log a warning (this is exactly the "invalid sequence" case the review flagged,
   so surfacing it via log instead of an exception preserves the diagnostic value without new
   crash risk):
   ```python
   def _transition_state(self, new_state: str, run_id: int | None) -> None:
       old_state = self._state
       try:
           self._state_machine.transition_to(CrawlState(new_state))
       except ValueError as e:
           logger.warning("Invalid crawl state transition: %s", e)
       self._state = new_state
       if run_id is not None:
           self._emit_event("on_state_changed", run_id, old_state, new_state)
   ```
   Keep `self._state` as the string it already is elsewhere (UI code compares against
   `CrawlState.X.value` in several places — don't change that contract) — the state machine
   here is purely a validator/logger, not the source of truth for `self._state`.

### Files to touch

- `src/mobile_crawler/core/crawl_state_machine.py` — matrix edges (see above).
- `src/mobile_crawler/core/crawler_loop.py` — instantiate `CrawlStateMachine` in `__init__`,
  wire `_transition_state()` (line 517).
- `tests/core/test_crawl_state_machine.py` — update/add transition-matrix assertions.
- `tests/core/test_crawler_loop.py` — add a test asserting an invalid transition (e.g. call
  `_transition_state` with a bogus sequence) logs a warning instead of raising.

### Verification

1. Run a full crawl to completion (happy path) and confirm no new warnings appear, and the
   run still ends in `STOPPED`.
2. Force an error path (e.g. raise inside the crawl) and confirm `ERROR -> STOPPED` still
   works without warnings.
3. Exercise step-by-step mode (pause + advance) and confirm `RUNNING <-> PAUSED_STEP` still
   transitions cleanly.
4. `pytest tests/core/test_crawl_state_machine.py tests/core/test_crawler_loop.py`.

---

## Part 2 — `StepPhaseStateMachine.get_phase_duration` returns `None` on same-tick transitions

### Failing test

```
tests/domain/test_step_phase.py::TestStepPhaseStateMachine::test_get_phase_duration
AssertionError: assert None is not None
```

### Root cause

`src/mobile_crawler/domain/step_phase.py:117-142`:

```python
def get_phase_duration(self, phase: StepPhase) -> float | None:
    if phase not in self._transition_times:
        return None

    phase_entry = self._transition_times[phase]

    # Find the next phase that was entered after this one
    next_entries = [
        t for t in self._transition_times.values() if t > phase_entry
    ]
    if not next_entries:
        return None

    return min(next_entries) - phase_entry
```

It looks for "the next phase's entry time" by scanning **all** recorded timestamps
(`_transition_times.values()`, keyed by phase — see `transition_to()` at line 83:
`self._transition_times[new_phase] = time.monotonic()`) and taking the smallest one strictly
greater (`>`) than `phase_entry`.

`time.monotonic()` has finite resolution. In a fast unit test (or just fast real execution),
two back-to-back `transition_to()` calls can land on the exact same tick, so the "next" phase's
timestamp ties with `phase_entry` exactly. Strict `>` excludes the tie, `next_entries` comes
back empty, and the method returns `None` even though a subsequent transition genuinely
happened — which is exactly what `test_get_phase_duration` catches: it transitions
`CAPTURE -> DECIDE` and immediately asserts `get_phase_duration(CAPTURE) is not None`.

### Fix

Don't just change `>` to `>=` on `.values()` — that would also match `phase`'s **own** entry
(since `phase_entry` is itself a value in `_transition_times`), making `get_phase_duration`
wrongly return `0.0` for a phase that has *no* subsequent transition yet (the "still in this
phase" case, which must stay `None`). Exclude the phase's own entry by key, not by value:

```python
def get_phase_duration(self, phase: StepPhase) -> float | None:
    if phase not in self._transition_times:
        return None

    phase_entry = self._transition_times[phase]

    # Find the next phase that was entered at or after this one (ties are
    # possible: time.monotonic() resolution can put two fast transitions on
    # the same tick), excluding the phase's own entry.
    next_entries = [
        t for p, t in self._transition_times.items()
        if p != phase and t >= phase_entry
    ]
    if not next_entries:
        return None

    return min(next_entries) - phase_entry
```

Note: this still has a latent design limitation worth flagging to whoever picks this up but
not necessarily fixing here — `_transition_times` is keyed by `StepPhase`, so re-entering a
phase (e.g. `CAPTURE -> DECIDE -> CAPTURE`) overwrites that phase's earlier timestamp. If a
step ever loops back through an earlier phase, `get_phase_duration` for phases in between can
give a misleading answer. Not exercised by the current test suite (phases appear to progress
linearly per step in practice) — call this out if you touch this file again, but it's out of
scope for the failing-test fix.

### Files to touch

- `src/mobile_crawler/domain/step_phase.py:117-142`

### Verification

```
pytest tests/domain/test_step_phase.py -v
```

All `TestStepPhaseStateMachine` cases should pass, including
`test_get_phase_duration` and `test_get_phase_duration_multiple_phases` (or equivalent) without
weakening any existing assertions.
