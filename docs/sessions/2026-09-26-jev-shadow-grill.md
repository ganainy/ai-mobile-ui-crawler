---
author: claude
date: 2026-09-26
---
# Jev shadow spike: design grill

Grill (no code) on whether TypeSafe's Jev (a "System One" model: text state + typed questions in, calibrated Choice/Noul/Score out, no image input, early access) can speed up the crawler. Design agreed; not yet filed as an issue or built.

## Findings
- Real crawls send the LLM no images: `vision` defaults to `False` for Manager/Executor/FastAgent and `crawler_agent_service.py` never sets it. The prompt gets the indexed element list; an icon-only element is labelled text → contentDescription → resourceId → className (`indexed_formatter.py:272`), or OmniParser's `content` when the a11y tree is incomplete.
- The Executor mostly grounds a Manager subgoal to an element index, which fits Jev; the Manager (free-text planning) does not. Any speed-up is capped by the Executor's share of step time.
- Jev is reachable through OpenRouter with the existing OpenRouter key (`TYPESAFE_BASE_URL=https://openrouter.ai/api`); model ids `typesafe/jev-1.13`, `~typesafe/jev-latest`, `typesafe/jev-router`. Sources were search snippets; typesafe.ai and openrouter.ai are blocked from the cloud container.

## Decisions
- Shadow-only spike on the Executor (reasoning mode): Jev answers `Choice` `action` + `index` (+ swipe direction) from subgoal + element list; compared to the Executor's first batched action; typing steps excluded; never acts, never blocks, errors ignored.
- Output: `jev_shadow.jsonl` in the run folder (incl. which model answered) + a summary script; no DB/Run Report changes.
- Model `~typesafe/jev-latest` by default, editable.
- Enabled from a new Settings **Experimental** tab (checkbox, model field, note), saved as `jev_shadow_enabled` (off by default), CLI via `config set`; no env var. On but no key / no SDK → Pre-run Warning.
- Go/no-go: at confidence ≥0.85 agreement ≥90%, covering ≥50% of Executor steps, median latency <500 ms, and Executor ≥~25% of step time; disagreements spot-checked.
- Glossary: added **Experimental Feature**; Pre-run Warning examples extended.

## Follow-ups
- User to confirm the design, then file it as a GitHub issue.
- Installing `typesafe-sdk` into `.venv312` needs the user's OK.
