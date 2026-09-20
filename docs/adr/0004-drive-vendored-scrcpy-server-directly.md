---
author: claude
---
# Drive a vendored scrcpy server directly for the Live Feed

The Live Feed needs raw device frames inside the Qt window so parsed-element boxes can be drawn over them. The scrcpy CLI can't hand frames to another process on Windows (only its own window or `--record=file`), so we push the pinned `scrcpy-server` jar (v3.3.4, Apache-2.0, committed under `src/mobile_crawler/resources/scrcpy/`) with the project's own adb, forward its socket, and decode the raw H.264 stream with PyAV. The user's installed scrcpy is never used.

The cost is depending on the server's undocumented command-line and startup protocol, which changes between scrcpy versions. We accept that by pinning: the server refuses to start when its version argument differs from the jar, so `SERVER_VERSION` and the jar file move together, and upgrading is a deliberate act, not a side effect.

## Considered options

- **scrcpy CLI as a subprocess** — maintained protocol handling, but frames can't reach Python without embedding its window (no overlay possible) or tailing a recorded file (seconds of latency). Rejected.
- **`adb exec-out screenrecord` to stdout** — no jar needed, same decode path, but a 3-minute cap per stream and higher latency. Kept as the fallback if the jar ever breaks on a new Android release.
