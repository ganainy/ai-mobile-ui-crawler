---
author: claude
updated: 2026-09-27
---
# Remove `skip_authentication`; PCAP pull hits the 30s ADB default

Debugging run 204 (Whisk, Google-only sign-in) surfaced two separate problems.

## 1. `skip_authentication` removed

Run 204's agent hit an empty Manager LLM response mid Google-consent-flow, then pressed
Back twice (against the goal text's own instruction) and called `skip_authentication`
with a false justification ("requires unknown password") after only one account tap. The
user asked to remove the tool outright: the agent should never be able to voluntarily
give up on sign-up/login.

`domain/authentication.py`:
- Deleted the `skip_authentication` tool entry and its `_skip_authentication` handler.
- `goal_section()` and `_GOOGLE_SIGN_IN_RULE` no longer tell the agent to call it; they
  now say to keep retrying / look for alternate paths and only stop once a code tool
  itself reports the attempt cap.
- The attempt-cap (`_begin_attempt`) and Human-Fallback-declined (`_ask_human`) paths are
  unchanged as *automatic* safety valves (they still set `skipped_reason`, still return
  `False` so the agent stops retrying that tool) — those aren't the agent voluntarily
  giving up, they're the system stopping a pointless retry loop. Renamed `_SKIP_HINT` ->
  `_GIVE_UP_HINT` and rewrote it to not mention a tool that no longer exists.
- `prompts.py`'s tool list updated to match.

Tests: removed `test_skip_authentication_tool_records_reason`; updated the tool-set
assertion in `test_crawler_agent_service.py` and the cap-reached message assertion in
`test_authentication.py`. Full suite green. Not tried on the phone.

## 2. PCAP pull timeout (same bug class as the 2026-09-26 video fix)

Run 204's pcap was lost: `adb pull` of the capture file hit `ADBClient`'s 30s default
timeout and was killed (`Command timed out after 30.0s`), leaving `stop_capture_and_pull_async`
return `None`. This is the same root cause as [2026-09-26's video segment
timeout](2026-09-26-video-pull-timeout.md) — `TrafficCaptureManager._run_adb_command_async`
never had a `timeout` parameter at all, so every call (including the pull) used the
client's 30s default regardless of file size.

`domain/traffic_capture_manager.py`:
- `_run_adb_command_async` now accepts and forwards a `timeout` kwarg (mirrors
  `VideoRecordingManager`'s helper).
- The PCAP pull uses a new `PULL_TIMEOUT_SECONDS = 300.0`.
- A failed pull now deletes the truncated local file, matching the video fix (the killed
  pull can leave a partial, unreadable pcap; the device copy is kept since `rm` only runs
  after a successful pull elsewhere in this file).

Also answered a related question: SNI extraction (`pcap_extract_sni`, default on) writes
`<pcap_filename>.sni.txt` next to the `.pcap` in the run's `pcap/` folder, but only after
a *successful* pull (`_extract_sni_report` is called from inside the success branch) — so
a run whose pull times out (like 204) has no `.sni.txt` either, which is why the user
didn't see one.

Tests: fixed three tests broken by the new `timeout` kwarg (`test_adb_commands_include_device_id_when_provided`,
`test_extracts_sni_report_after_successful_pull`, `test_skips_sni_extraction_when_disabled`)
and added `test_pcap_pull_uses_long_timeout`. Full suite green. Not tried on the phone —
run 204's pcap is presumably lost since the device copy is deleted after a successful pull
by `_cleanup_device_pcap_file_async`, but only on success; if the run was recent the device
copy may still be under `/sdcard/Download/PCAPdroid/` for a manual `adb pull`.
