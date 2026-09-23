---
author: claude
date: 2026-09-23
---
# 10-minute CLI crawl of MyFitnessPal (run 179)

Command: `crawl --device adb-RFCR31561LM-8O0fCF._adb-tls-connect._tcp --package com.myfitnesspal.android --provider gemini --model gemini-3.8-flash --parser-mode boost --no-human-fallback`.

## Result
- Run 179, COMPLETED, stop reason `duration_limit` after 10 min 44 s, 38/38 steps ok, 36 AI calls, 36 screenshots. Report and Analysis Bundle written to `%APPDATA%/mobile-crawler/output_data/run_179_20260923_124806/` (first real check of #6 / #22 / #24: `steps.jsonl` has 38 lines, timing breakdown filled).
- The agent spent the whole run in MyFitnessPal's sign-up onboarding (goal, barriers, habits, activity, sex, age, country, height, weight, email, password), hit an error dialog on submit and was ticking the Terms checkbox when time ran out. Never reached the main app.

## Problems found
- **`crawl --duration` does not work** (#25, `--steps` too). It saves `max_crawl_duration_seconds`, but `CrawlerLoop` reads `max_duration_seconds` first and only applies a time limit when `limit_type == "duration"`. Workaround used: `config set limit_type duration` + `config set max_duration_seconds 600`, restored to `steps` / `60` afterwards.
- **Portal never gave an a11y tree** (37/37 captures `no_tree`, every step fell back to OmniParser on Replicate, ~5-7 s each; capture phase avg 13.6 s, max 30 s). `adb shell settings get secure enabled_accessibility_services` returned `null`: the Portal accessibility service is not enabled on the phone. So no `a11y_checks` tuning data from this run.
- **No `run_stats` for CLI runs**: `stats 179` says no persisted statistics; only the GUI (`main_window.py`) saves them.
- "Unique screens visited: 0" in the bundle (screen ids are never assigned, known from #24).
- Phoenix was not running, so tracing was off.
