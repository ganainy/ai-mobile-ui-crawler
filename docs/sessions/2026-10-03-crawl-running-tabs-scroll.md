---
author: claude
updated: 2026-10-03
---
# Keep Settings tabs and scrolling usable during a crawl

User report: while a crawl runs, the Settings tabs could not be switched and the panel could not
be scrolled. The locking of config inputs is wanted; the navigation is not.

## Root cause

`MainWindow._update_crawl_ui_state` called `setEnabled(not running)` on the whole `SettingsPanel`.
Disabling a widget disables its children, so the Settings `QTabWidget` tab bar and every
`QScrollArea` inside the tabs stopped responding, not just the inputs.

## Change

- `ui/main_window.py`: `settings_panel` is no longer in the whole-widget toggle list. The device,
  app and AI selectors are still disabled as before.
- `ui/widgets/settings_panel.py`: `set_crawl_running` now locks only input controls
  (`_LOCKABLE_INPUTS`: buttons, line edits, combo boxes, spin boxes, sliders, text edits). It
  records the ones it disabled (`_locked_inputs`) and re-enables exactly those on unlock, so
  controls already disabled by their own toggles (e.g. the max-duration field, or Phoenix/Langfuse
  settings while tracing is off) stay disabled. Tab bars, scroll areas and scroll bars are not locked.
- Tests: `TestCrawlRunningLocksInputsOnly` in `tests/ui/test_settings_panel.py`.

## Known gaps

- Save and Reset Layout buttons are inside the panel, so they are locked during a run as before.
- A control the panel re-enables during a run (e.g. the Generate Guided Scenarios button, whose
  busy handler calls `setEnabled(not busy)`) would be re-enabled by that handler; unlikely to
  matter since that action does not start during a crawl.
- The Logs / AI Monitor tabs in the right panel are not disabled by any code path found, so
  whatever blocks them during a run is still unexplained. Not reproduced.

## Verification

`tests/ui/test_settings_panel.py` green. `tests/ui/test_main_window.py` has two failures, both the
known pre-existing `stats_dashboard` AttributeError. Not checked by clicking through the running GUI.
