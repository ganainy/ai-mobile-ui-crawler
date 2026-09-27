---
author: claude
updated: 2026-09-27
---
# Target Recovery redesign: one mechanism, tolerant by default

User report: Whisk (`com.google.android.apps.labs.whisk`) tried to complete Google Sign-In and got yanked back to its own login screen — `Target app mismatch before state capture (current=None, target=com.google.android.apps.labs.whisk)`. Grilled the underlying design instead of patching in another one-off exception.

## Findings
- `current=None` was a transient, unresolvable foreground read during the Google Sign-In hand-off — not a missing package in an allowlist. `provider.py`'s guard treated any unclassified/`None` foreground as `kind=None, grace=0` -> immediate relaunch.
- A second, independent guard existed: `context_guard.DeviceContextCapture` + `AppSwitchRecovery` (feature "04-01/02/03", committed `43023a1`), wired into `CrawlerAgentService`, running after every action with **zero** grace/exceptions and a hard `FatalError` abort after 3 failed relaunches. None of the three prior incident fixes (browser login 09-19, permission dialogs 09-25, Google Sign-In 09-26) ever touched it — all three only patched `provider.py`.

## Design (grilled, not just patched)
1. Deleted `AppSwitchRecovery`/`DeviceContextCapture` and their wiring/abort path entirely (`context_guard.py`, `crawler_agent_service.py`). `UIDumpValidator`/`StepSkipReason.INVALID_UI_DUMP` (unrelated: UI dump shape, not app identity) kept.
2. `provider.py`'s `_ensure_target_package_active` inverted: default is now *tolerate*, not *relaunch-unless-allowlisted*. `BROWSER_PACKAGES`/`SYSTEM_DIALOG_PACKAGES` and their separate grace tiers (40 / 5 / 0) removed; one `target_recovery_grace_captures` (default 40, reusing the browser tier's empirically-tuned value) applies to any foreign foreground including an unresolvable `None`.
3. `com.google.android.gms` (`UNLIMITED_GRACE_PACKAGES`) is the one kept exception — Google Sign-In duration is genuinely unbounded.
4. If recovery is eventually attempted (grace exhausted) and the relaunch itself fails 3x, still raises `RuntimeError` (unchanged) — a broken device/app is a different failure class than a legitimate external flow.
5. No other relaunch call sites touched (`restart_app_before_run`, initial launch); no Settings/config surface added (these values were never user-exposed).

`CONTEXT.md` gained **Target Recovery**. [ADR 0006](../adr/0006-one-target-recovery-mechanism.md) records why one mechanism replaces two.

## Tests
`tests/domain/test_droidrun_target_package_guards.py`: collapsed the browser/system-dialog grace-exhaustion tests into one parametrized `test_state_provider_relaunches_after_default_grace_exhausted` (browser, system dialog, unclassified app, `None` — all share the same grace now); added `test_state_provider_tolerates_unresolvable_or_unrecognized_foreground` as the direct regression test for the Whisk case; gms unlimited-grace test now runs 50 captures (past the new default of 40) to prove it's actually unlimited. `tests/domain/test_crawler_agent_service.py`: updated the two wiring tests to check the ADB executor gets wired instead of the removed `DeviceContextCapture`/`AppSwitchRecovery`; dropped dead `_context_capture` assignments from the tool-execution tests.

Full suite green except the two pre-existing, unrelated `stats_dashboard` failures in `tests/ui/test_main_window.py` (present on `main` before this session).

**Not done:** verification against a real Whisk Google Sign-In on the phone — the user asked for this specifically given the guard's track record (three prior "not tried on the phone" patches, one of which still had this bug). Should happen before this is considered closed.
