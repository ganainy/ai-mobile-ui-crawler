---
author: claude
---
# Notify hook debug (2026-09-19)

No `src/` changes made this session; the uncommitted `src/` edits pre-date it.

Diagnosis of spurious "Claude finished" / "needs your attention" toasts from `~/.claude/settings.json` hooks + `~/.claude/notify.ps1`:
- Global Stop hook is async and runs in parallel with `scripts/stop_hook_state_reminder.py`, which blocks the stop (exit 2) when `src/` is dirty and `docs/STATE.md` is not. The toast fires even though Claude continues.
- Notification hook has no `matcher`, so `idle_prompt` / `auth_success` also trigger it.

Proposed (not yet applied): matcher `permission_prompt|elicitation_dialog` on Notification; in `notify.ps1` for Stop, sleep ~2s and skip if the transcript changed.
