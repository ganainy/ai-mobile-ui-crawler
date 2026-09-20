---
author: claude
updated: 2026-09-20
---
# Project State

Entry point for the Obsidian vault (`docs/`). Claude reads this first each session and updates it before finishing substantive work.

## Now
- Live Feed: the Stats panel's Screenshot board is now a live view of the selected device (vendored scrcpy 3.3.4 server over adb, wireless included), with fading element boxes; falls back to the last screenshot. Unit-tested and streamed against a real phone outside a crawl; not yet seen in a full run. See [session](sessions/2026-09-20-live-feed.md), [ADR 0004](adr/0004-drive-vendored-scrcpy-server-directly.md).
- Device selector auto-retries (3x, 1.5 s) at startup before the "No Devices Found" dialog and picks the last-used device when several are connected. Unit-tested, not tried on a device. See [session](sessions/2026-09-20-device-auto-refresh.md).
- Auth scenario text now forbids logging in with the generated sign-up credentials (run 174 tried to log in with them on an email-first web form). Runs 172/173: guard relaunched Headspace during its web login in Brave. Guard now tolerates a browser for up to 40 captures; manager screenshot now comes from the same capture as the parsed elements (was mismatched). Tests pass; not tried on a device. `open_app` app-list lookup (~50s, serial dumpsys) now concurrent + cached. See [session](sessions/2026-09-19-browser-login-guard.md).
- Run 171 died at step 2: executor (Gemini `max_tokens` 512) got `MAX_TOKENS` 3x. Raised LLM profile limits in `crawler_agent_service.py` (manager 8192, executor 4096, app_opener 2048). Verified by the user on a real run. See [session](sessions/2026-09-19-max-tokens-executor.md).
- Notify-hook debug: spurious toasts come from the async global Stop hook firing when the project Stop hook blocks, and an unmatched Notification hook. Fix proposed, not applied. See [session](sessions/2026-09-19-notify-hook-debug.md).
- Test Email field removed; "Test" dropped from the Address and Mobile Number labels (email now from App Account override / Verification Inbox); phone auto-detected from SIM via adb, manual field overrides. Uncommitted; not tried on a real device. See [session](sessions/2026-09-19-remove-test-email-detect-phone.md).
- Old issues #1 and #5 verified fixed and closed; stray `src/=0.4.26` removed. See [session](sessions/2026-09-19-close-old-issues.md).
- Issue #7 (App Accounts) committed as cf3196f: per-app account store, Settings "App Account" group, account injected into the agent goal. See [session](sessions/2026-09-19-app-accounts.md).
- Vault set up 2026-09-19: docs reorganised, shipped feature specs, old plans and fixed-bug handovers deleted (see git history).
- Recent: local OmniParser Docker auto-start at GUI launch; Docker stop dialog / taskbar icon / Stop button polish; App Web Profile -> Guided Scenarios wired end-to-end.

## Next / blockers
- Issue #6 (Run Report + Analysis Bundle): committed as c7f016f (tests not re-run after the last edits, incl. fixes for 7 pre-existing failures); not yet run on a real device or against a live Phoenix/Langfuse server. See [session](sessions/2026-09-19-run-report-analysis-bundle.md).
- Auth / sign-up / OTP support: design agreed 2026-09-19, issues #7-#11 (#11 blocked by #7-#10). #7 App Accounts done ([session](sessions/2026-09-19-app-accounts.md)); #8 Verification Inbox done and pushed (9a000f0, a09e36b; [session](sessions/2026-09-19-verification-inbox.md)); #9 SMS reader committed; #10 Human Fallback pushed (1795e86, [session](sessions/2026-09-19-human-fallback.md)), but its Settings group is still uncommitted in `settings_panel.py` alongside #6-#8 hunks; #11 Authentication scenario implemented ([session](sessions/2026-09-19-authentication-scenario.md)), needs a manual check on a real app with email verification. See [session](sessions/2026-09-19-auth-verification-design.md).
- Test suite sped up to ~3.5 min (2bbbba6); see [session](sessions/2026-09-19-authentication-scenario.md). Keyboard handling: `AndroidDriver.hide_keyboard` (BACK only when `mInputShown=true`) is called by `AndroidStateProvider._dismiss_keyboard` before every screenshot, so the keyboard no longer hides elements or gets parsed by OmniParser; executor prompt updated. Unit-tested, not tried on a device; IME-bounds filter for OmniParser not done. See [session](sessions/2026-09-19-hide-keyboard.md).
- Next: verify #6 on a real run, then run the crawler on ~10 health apps and analyse the bundles.

## Map of the vault
- [Glossary](Glossary.md) - stub pointing at root `CONTEXT.md`
- [code/](code/_index.md) - generated code-structure notes
- [adr/](adr/) - architecture decisions
- [architecture/](architecture/ARCHITECTURE.md) - architecture + README-style guides ([index](architecture/readmes/INDEX.md))
- [sessions/](sessions/) - Claude's dated session logs
- [notes/](notes/) - the user's own notes; Claude reads, never edits

## Code structure
- [code/](code/_index.md) is the generated map of every module: classes, public functions, imports and imported-by links. Regenerated by `scripts/gen_code_notes.py` via the pre-commit hook (`pre-commit install` once per clone). Package summaries are hand-written between the `summary` markers.

## Outside the vault
- Tasks and specs: GitHub issues in `ganainy/ai-mobile-ui-crawler`.
- `specs/013-app-auth-signup`, `specs/015-responsive-ui`: old unfinished specs kept because their status is unclear (auth/signup code appears removed).
- `.planning/`: open text-entry hardening notes and todos (June 2026).
