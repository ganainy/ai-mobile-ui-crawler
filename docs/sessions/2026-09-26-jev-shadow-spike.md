---
author: claude
updated: 2026-09-26
---
# Jev shadow spike (issue #29)

**Goal:** log TypeSafe Jev's element pick next to the Executor's, never acting on it, to decide whether a Jev-first Executor is worth building. (The grill note the issue cites, `2026-09-26-jev-shadow-grill.md`, does not exist in the repo; the issue text was the spec.)

**Built**
- `domain/jev_shadow.py`: question building (`action`, `index`, `direction` as `Choice`), action normalisation, comparison, `JevShadow` (start/finish/aclose, JSONL writer). One SDK call per step asks all three questions; direction is only logged when Jev's action is `swipe` (a second call would add latency for nothing).
- `ExecutorAgent.get_response` starts the Jev task before the LLM call and hands it to `finish()` afterwards; a background recorder writes the line, so the step never waits. `finish` is also called on LLM failure (line with no executor action).
- Service attaches it after the agent is created (`_attach_jev_shadow`), closes it in `cleanup`. `CrawlerLoop` sets `jev_shadow_path` = `RunFolderLayout.jev_shadow` = `reports/jev_shadow.jsonl` (under `reports/` per #26, not the run root).
- Settings "Experimental" tab (5th); Pre-run Warning `_jev_shadow_warning`; both settings in the config snapshot.
- `scripts/jev_shadow_summary.py`.

**Tests:** `tests/domain/test_jev_shadow.py` (fake client), `test_jev_shadow_service.py`, executor hook tests in `test_executor_action_batch.py`, pre-run warning, settings panel, summary script. Suite 1900 passed.

**Not done / notes**
- Not tried against the real Jev API or a real crawl; the model id `~typesafe/jev-latest` and OpenRouter base URL are from the issue.
- Jev `confidence` in the log is the weakest of the answers that matter (action, plus index for click/long_press or direction for swipe).
- SDK retries are off (`max_retries=0`, 20 s timeout) so logged latency is one round trip.
