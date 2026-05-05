# Phase 4: ADB Context Guardrails - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Ensure every crawl step captures and validates device context (package/activity), validates UI dumps before the decision layer processes them, and detects + recovers from unintended app switches. The crawler must never act on stale or wrong-app UI data.

</domain>

<decisions>
## Implementation Decisions

### Context Capture Timing
- **D-01:** Single capture in CAPTURE phase via DroidRun's existing `phone_state` (already calls `dumpsys window | grep mCurrentFocus`). No second ADB call post-EXECUTE.
- **D-02:** Pre-check in CAPTURE: compare current package against target app before proceeding to DECIDE. If mismatch, skip DECIDE/EXECUTE and go straight to app-switch recovery. This avoids wasted AI calls on wrong-app screenshots.

### UI Dump Validation
- **D-03:** Gate UI dump with two checks before the decision layer: parseable (XML parsed successfully) AND non-empty (at least 1 element in the tree). Existing `_quick_a11y_check` continues to run for quality signals but does NOT block.
- **D-04:** On validation failure: retry the ADB UI dump once (transient failures), then if still invalid, mark the step as SKIPPED and move to the next step. Never abort the run on a bad dump.

### App-Switch Recovery
- **D-05:** Use `adb shell am start` with the app's main launcher activity to navigate back to the target app. No BACK-press-then-launch — just direct am start. Simpler and always works.
- **D-06:** 3 consecutive recovery attempts before aborting the run. A systemic issue (app crash, device disconnected) should not loop forever.
- **D-07:** Always relaunch to the main launcher activity, not the last-known activity. Deep activity restoration may fail with unexported activities or missing intent extras. The crawler re-explores from the app's main screen.

### Context Persistence
- **D-08:** Extend `step_phase_repository` (and the `step_phases` DB table) with `current_package` and `current_activity` columns. Keeps all step data together; easy to query device context at any step.
- **D-09:** Persist only `current_package` and `current_activity` per step. Other context (screen size, SDK) rarely changes during a crawl and is not needed per-step.

### Agent's Discretion
- Exact am start command construction (how to resolve launcher activity from package)
- Whether to add the validation gate as a method on DroidRunAgentService or as a standalone utility
- Retry delay for UI dump retry (researcher/planner can determine appropriate wait)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Device Context & ADB
- `src/mobile_crawler/infrastructure/adb_client.py` — Async ADB command execution wrapper, the base for all ADB calls
- `src/mobile_crawler/domain/adb_action_executor.py` — Has `get_current_package()` (note: pipe syntax bug), `launch_app()`, `back()`, `home()` methods
- `external/droidrun/droidrun/tools/driver/android.py` — DroidRun Android driver; `_get_current_app()` already calls `dumpsys window | grep mCurrentFocus`; populates `phone_state` dict with `currentApp` and `packageName`

### UI Context & Validation
- `src/mobile_crawler/domain/ui_context.py` — `UIContextManager.get_context()` retrieves a11y tree + OmniParser fallback; `_quick_a11y_check()` has sparse/stale/clickable checks but runs after context retrieval, not as a gate
- `external/droidrun/droidrun/tools/ui/provider.py` — UI provider that combines a11y_tree, phone_state, device_context; validates required_keys=["a11y_tree", "phone_state", "device_context"]

### Step Phase & Persistence
- `src/mobile_crawler/domain/step_phase.py` — `StepPhaseStateMachine` with CAPTURE→DECIDE→EXECUTE→RECORD→CHECKPOINT transitions and listeners
- `src/mobile_crawler/domain/step_phase_models.py` — `StepPhaseTransition` dataclass
- `src/mobile_crawler/infrastructure/step_phase_repository.py` — SQLite persistence for step phases; will be extended with package/activity columns
- `src/mobile_crawler/infrastructure/database.py` — DatabaseManager, schema migrations

### Action Verification
- `src/mobile_crawler/domain/action_verifier.py` — Has `_get_current_app()` abstract method and `verify()` that checks navigated_away and action success
- `src/mobile_crawler/domain/models.py` — `ActionResult` with `navigated_away`, `was_retried`, `retry_count`, `recovery_time_ms` fields

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ADBActionExecutor.get_current_package()`: Already extracts package from `dumpsys window` output. Has a bug (pipe `|` passed as literal arg to subprocess) that needs fixing. Pattern is reusable for activity extraction.
- `ADBActionExecutor.launch_app()`: Uses `monkey -p package -c android.intent.category.LAUNCHER 1`. Will need `am start` variant for recovery (monkey doesn't restore activity stack reliably).
- `StepPhaseStateMachine`: Listener callback pattern can be used to inject context capture/validation at CAPTURE phase transition.
- `ActionVerifier.verify()`: Already checks for navigation away from app; pattern is reusable for app-switch detection.

### Established Patterns
- Step phase state machine: CAPTURE→DECIDE→EXECUTE→RECORD→CHECKPOINT with listeners on transitions
- DroidRun's phone_state dict: already provides `currentApp`, `packageName` per step via `android.py` driver
- Error model: typed exceptions (`CrawlerError`, `FatalError`, `CheckpointError`) from Phase 1
- `ActionResult.navigated_away` flag already signals when actions like back/home/recent_apps switch away

### Integration Points
- `DroidRunAgentService.execute_exploration_task()`: Main entry point where steps execute. Context guardrails hook in here at the step level.
- `StepPhaseStateMachine` CAPTURE transition: Where pre-check and validation gate should be injected.
- `step_phase_repository`: Where package/activity columns will be added.
- `database.py`: Where schema migration for new columns will be managed.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 4-ADB Context Guardrails*
*Context gathered: 2026-05-05*
