# Phase 4: ADB Context Guardrails - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 04-ADB Context Guardrails
**Areas discussed:** Context capture timing, UI dump validation, App-switch recovery, Context persistence

---

## Context Capture Timing

| Option | Description | Selected |
|--------|-------------|----------|
| CAPTURE only | Single capture at step start via DroidRun's existing phone_state. Post-action drift caught by next step's CAPTURE. | ✓ |
| CAPTURE + post-EXECUTE | Capture at step start AND after action execution. Adds ~100-200ms ADB call per step. | |

**User's choice:** CAPTURE only
**Notes:** Simpler approach; drift between steps caught at next CAPTURE's pre-check.

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-check in CAPTURE | If current package != target, skip DECIDE/EXECUTE and go to recovery. Avoids wasted AI calls. | ✓ |
| Record only, detect later | Record package but proceed. Separate step catches mismatch later. | |

**User's choice:** Pre-check in CAPTURE
**Notes:** Prevents wasting an AI call on wrong-app screenshots.

---

## UI Dump Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Parseable + non-empty | UI tree XML parsed AND has ≥1 element. Fast, catches broken dumps. | ✓ |
| Parseable + non-empty + min elements | Also require ≥5 elements to catch near-empty dumps like lock screens. Risks false positives. | |
| Parseable + non-empty + target app check | Also verify dump's root package matches target app. Catches webview-only screens. | |

**User's choice:** Parseable + non-empty
**Notes:** Minimal gate; existing _quick_a11y_check continues for quality signals but doesn't block.

| Option | Description | Selected |
|--------|-------------|----------|
| Retry dump, then skip step | Retry ADB UI dump once. If still invalid, mark step SKIPPED and continue. | ✓ |
| Retry dump, then abort run | Retry once. If still invalid, treat as fatal. Safer but more aggressive. | |
| Skip step immediately | No retry — just skip. Fastest but may skip unnecessarily on transient failures. | |

**User's choice:** Retry dump, then skip step
**Notes:** Balances robustness (handles transient failures) with crawl stability (doesn't abort on one bad dump).

---

## App-Switch Recovery

| Option | Description | Selected |
|--------|-------------|----------|
| Launch via am start | Use `adb shell am start -n package/activity` to relaunch target app. Reliable. | ✓ |
| Press back first, then launch | Try BACK first for system dialogs, then am start. | |
| Back repeatedly, then launch | Press BACK up to N times to dismiss overlays, then am start. Most robust but slower. | |

**User's choice:** Launch via am start
**Notes:** Direct and reliable; system overlays are rare in crawl scenarios.

| Option | Description | Selected |
|--------|-------------|----------|
| 3 attempts, then abort run | 3 consecutive recovery failures suggests systemic issue. Abort rather than loop. | ✓ |
| 3 attempts, then skip and continue | Skip failed step and continue. Risk of loop. | |
| 5 attempts, then abort | More forgiving but delays failure detection. | |

**User's choice:** 3 attempts, then abort run
**Notes:** Prevents infinite loops on systemic issues (app crash, device disconnected).

| Option | Description | Selected |
|--------|-------------|----------|
| Main launcher only | Always relaunch to launcher activity. Simpler, always works. | ✓ |
| Track and restore last activity | Remember last activity, try am start -n package/lastActivity. May fail with unexported activities. | |

**User's choice:** Main launcher only
**Notes:** Deep activity restoration is fragile; crawler re-explores from main screen.

---

## Context Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Extend step_phase_repository | Add package/activity columns to existing step_phases table. All step data together. | ✓ |
| Separate context table | New device_context table with step_id FK. Cleaner separation but requires join. | |
| In step_phase_models | Add fields to StepPhaseTransition dataclass alongside existing transition data. | |

**User's choice:** Extend step_phase_repository
**Notes:** Keeps step data co-located; easy to query context at any step.

| Option | Description | Selected |
|--------|-------------|----------|
| Package + activity only | Minimal, matches ROADMAP success criteria. Other context rarely changes. | ✓ |
| Package + activity + is_target_app | Also persist boolean flag for easy filtering of off-target steps. | |

**User's choice:** Package + activity only
**Notes:** is_target_app can be derived at query time; no need to persist it.

---

## Agent's Discretion

- Exact am start command construction (how to resolve launcher activity from package)
- Whether to add validation gate as a method on DroidRunAgentService or standalone utility
- Retry delay for UI dump retry

## Deferred Ideas

None — discussion stayed within phase scope.
