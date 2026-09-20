---
author: claude
date: 2026-09-20
---
# Action Batching: design agreed, batching implemented (not yet run on a device)

Trigger: run 175 (Headspace sign-up succeeded) used ~130k tokens for 15 steps / 367 s. Each step = Manager call + Executor call + two OmniParser captures. Sign-up took 7 steps for 3 form fields + submit.

## Decisions
- **Where**: Manager emits a compound subgoal; Executor returns an ordered list of actions in one call (`executor_agent.py`, `crawler_agent.py:run_executor`). Roles stay separate. Term: **Action Batch** (see `CONTEXT.md`).
- **Batch rules**: only type/select actions, then at most one final navigating click. Stop on first failure. Cheap check between actions (foreground package unchanged, no re-parse); on mismatch abort to Manager. Layout shift mid-batch (e.g. password rules pushing the button down) falls back to single-step replan.
- **Scope**: generic (forms and onboarding "select, then Next"), cap 5.
- **Capture reuse**: reuse the post-action capture as the next Manager state when the UI settled and nothing changed (removes the second capture per step).
- **Recording**: batch expanded into one history entry per action; `step_number`/`max_steps` count a batch once.
- **Setting**: Settings value "max actions per batch", default 5, 1 = current behaviour.
- **Success metric**: on the same Headspace sign-up flow vs run 175: >=40% fewer tokens, >=35% less wall-clock (7 steps -> ~3).

## Implemented (unit-tested, not tried on a device)
- `parse_executor_response` returns `actions` (single object or JSON array). `ExecutorAgent` runs the batch: stops on first failure, after any non-type action, on foreground-package change, at `max_actions_per_batch`; one UI-settle wait after the last action; result carries `results` per action.
- `CrawlerAgentState.record_executor_result`: one history entry per action, `step_number` untouched. `run_executor` uses it.
- `AgentConfig.max_actions_per_batch` (default 5, 1 = off), `config_example.yaml`; passed to Executor/Manager; foreground reader in `CrawlerAgent._foreground_package_reader`.
- Manager and Executor prompts gain batching instructions only when the value is > 1.
- Tests: `tests/domain/test_executor_action_batch.py`, `test_executor_batch_recording.py`, `test_action_batch_config.py`.

- Capture cost, root cause found instead of "reuse": `ui_parser_mode = boost` was not treated as OmniParser-backed, so the post-action UI-settle wait polled `get_state()` (a full Replicate OmniParser parse, ~6 s) instead of cheap screenshot hashing, then the Manager parsed again. New `is_omniparser_backed()` (omniparser + boost) now drives `UIWaitPredicate`, `crawler_agent_service` and `ActionVerifier`. Tests in `tests/domain/test_ui_wait_predicate.py`.

## Not done
- Settings panel control for the batch size (config file only for now).
- Run 175's Analysis Bundle had empty `steps.jsonl`/`step_logs`/`screens`/`transitions` (bug, separate).
- Real Headspace run vs run 175 baseline (131,560 in / 3,673 out tokens, 32 LLM calls, 367 s; Manager 64% of input tokens, LLM time only ~80 s).
