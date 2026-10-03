---
author: claude
---
# Stop the run clearly when the AI model fails

Trigger: run 209 (Whisk, `opencode_go` / `deepseek-v4.1-flash`) ended after the Manager returned empty content 3x; the user only saw a log line and wants a clear message and an alert for any model failure (error, empty reply, no credit/usage).

- `domain/llm_errors.py`: `LLMCallError(message, kind)`, `classify_llm_error`, `is_fatal_llm_error`, `find_llm_call_error` (walks `__cause__`).
- `inference.py`: fatal errors (401/402/403, 400/429 with quota/credit/balance text) raise at once; otherwise 3 attempts then a classified error (message names the model).
- `crawler_agent_service.py`: an `LLMCallError` anywhere in the cause chain skips the transient-retry and crash-relaunch branches (the transient token list contains "timeout", "retry", "capacity"), returns `final_state["llm_error_kind"]`.
- `crawler_loop.py` emits `on_error` with an `LLMCallError`; `main_window._on_run_error` logs + `QMessageBox.critical`. CLI already prints `on_error` and the stop reason.
- Not done: `crawl_batch` still continues to the next app after a model failure; the Executor's old "empty reply -> invalid action" recovery is bypassed on purpose; the Manager `[DONE]` subgoal handoff bug is separate.
- Tests: `tests/domain/test_llm_errors.py`. Other failures in the full run (`stats_dashboard`, `test_session_folder_open`) are the known ones; two `test_portal_actions` failures appear only in the full run, pass alone.
- Follow-up: the user's provider console showed every run-209 request as successful, so the empty Manager reply is an HTTP 200 with no text. Cause not found (raw reply was never stored; `ai_interactions.response_raw` is NULL for the failed call). `inference.describe_empty_response` now adds finish_reason, reasoning/refusal/tool-call content, token usage and block types to the "returned empty content" warning; re-run and read that line.
