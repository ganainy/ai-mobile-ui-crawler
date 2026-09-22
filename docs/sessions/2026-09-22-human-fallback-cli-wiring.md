---
author: claude
---
# Issue #14: CLI Human Fallback wiring + --human-fallback flag

## What changed
- `HumanFallbackConfig.from_store` gained an `enabled_override: bool | None` param: `None` reads the persisted setting as before, otherwise the override wins for that call only.
- `CrawlerAgentService` gained `human_fallback_enabled_override` (mirrors the existing `human_prompter` attribute), consumed in `_build_auth_session`.
- `CrawlerLoop` gained a matching constructor param, forwarded onto the agent service in `run()` alongside `human_prompter`.
- New `mobile_crawler.cli.terminal_human_prompter.TerminalHumanPrompter`: a `HumanPrompter` implementation for the CLI, terminal-equivalent of the GUI's `QtHumanPrompter`. Reads stdin on a background thread (no native cross-platform stdin timeout) and waits on a queue with the configured timeout; blank/`skip` input skips authentication.
- `crawl.py`: always passes a `TerminalHumanPrompter()`; new `--human-fallback/--no-human-fallback` (default `None`) flows straight into `human_fallback_enabled_override` — never written to the config store, so it doesn't persist.

## Bug found and fixed during `/code-review`
The Spec-axis sub-agent caught a real defect: `TerminalHumanPrompter` spawned a fresh daemon thread per call. `input()` can't be cancelled, so a timed-out call left its thread blocked on stdin forever. Authentication can call the prompter more than once per run (`get_email_code` falling back to `get_sms_code`, both routing through `HumanFallback.request`), so a second prompt would start a *second* thread also reading stdin — a race that could silently swallow the user's answer to the current prompt. Fixed by tracking the pending reader on the instance and having a new call reuse it instead of starting another, so only one thread ever reads stdin at a time. Covered by `test_second_call_after_a_timeout_reuses_the_pending_reader_instead_of_racing_stdin`.

## Review outcome
- Standards axis: no hard violations; two judgement-call smells noted (a Data Clump from the prompter/override pair threading through 3 layers, and a dense ternary in `from_store`) — both left as-is, consistent with existing patterns.
- Spec axis: all four scope bullets from issue #14 implemented; the stdin-race bug above was the only real defect, now fixed.

## Status
Full test suite green. Not exercised against a real terminal/device — only unit/CLI-invocation tests. Committed to `main`.
