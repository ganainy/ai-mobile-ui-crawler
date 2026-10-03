---
author: claude
date: 2026-10-03
---
# Run 207 debug: empty a11y tree in a browser killed the crawl

Fixed after the debug (main fix only, per the user).

## What happened
Run 207 (Whisk, `accessibility` parser mode) crawled ~20 actions and 15 screens, then step 20 tapped "See activity", which opened `com.brave.browser`. The foreground guard allowed the capture (tolerant grace, 40 captures), Portal returned no a11y tree for the browser, and `AndroidStateProvider.get_state` (`tools/ui/provider.py`, the `ui_parser_mode == "accessibility"` branch) raised `RuntimeError("Accessibility mode has no accessibility tree ...")`. Nothing caught it, so the whole run ended ("0 steps", the summary counters are an artifact of the exception path).

The error text ("Install and enable Portal") is misleading: the tree worked for the previous ~19 steps.

## Fix
`AndroidStateProvider.get_state` now loops the screenshot + tree capture: in accessibility mode an empty tree triggers `_recover_from_empty_a11y_tree` (relaunch the target app via the new `_relaunch_target_app`, also used by the foreground guard) and a recapture, up to `empty_a11y_retries` (default 2); only then the old `RuntimeError`. Two tests added. Not done: OmniParser fallback, Manager awareness of leaving the app. Not tried on the phone.

Related: [Target Recovery redesign](2026-09-27-target-recovery-redesign.md), [ADR 0006](../adr/0006-one-target-recovery-mechanism.md).
