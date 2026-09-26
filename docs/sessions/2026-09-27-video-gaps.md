---
author: claude
---
# 2026-09-27 video gaps in run 201

Symptom: 10 min run, 3 video files, ~7 min total.

Log timeline: segment 1 recorded 23:57:09-00:00:09 (180 s cap), "saved" 00:02:43, so the pull blocked ~2.5 min; segment 2 started only after that (00:02:43), pull done 00:06:26; segment 3 ran until stop. Recorded ~180+180+~60 s.

Cause: `_segment_loop` did wait -> pull -> start next, so every pull was a gap.

Fix: start next segment first, pull in a background task; stop awaits pending pulls; segments sorted by part in manifest. Restart backoff if screenrecord exits in <2 s (avoids a tight loop, and the mocked tests).

Open: why `adb pull` took minutes; not investigated.

## Follow-up: pcap size and TLS

The 75 MB pcap is all Flow traffic (filter works): one Google server, front-loaded, hosts `www.gstatic.com` and `aisandbox-pa.googleapis.com`. Decryption is requested but not happening on the phone. Issue #31 and `docs/emulator-tls.md` describe the rooted-emulator route (untested). Commit d8bd316.
