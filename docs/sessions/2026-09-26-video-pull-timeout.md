---
author: claude
updated: 2026-09-26
---
# Video segment pull timeout (run 195)

**Symptom:** run 195's saved videos would not play in PotPlayer ("file exists, but does not seem to have any video"); log had `Failed to pull video segment: Command timed out after 30.0s`.

**Cause:** `VideoRecordingManager._pull_current_segment` ran `adb pull` with `ADBClient`'s 30 s default timeout. The killed pull left a truncated `.mp4` (no `moov` atom) in `videos/`. `stop_recording_and_save_async` also returned the path of a segment whose pull had failed.

**Fix (`domain/video_recording_manager.py`):**
- `adb pull` uses `PULL_TIMEOUT_SECONDS = 300`.
- A failed pull deletes the partial local file (the device copy stays, since `rm` only runs after a good pull).
- Segments with an `error` no longer count as saved.

Test: `test_failed_pull_removes_truncated_file_and_uses_long_timeout`. Not tried on the phone.

**Run 195:** the segments are probably still on the phone under `/sdcard/mobile-crawler/videos/` (if not since removed); `adb pull` them by hand. Local partial files can't be repaired.
