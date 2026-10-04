---
author: claude
date: 2026-10-04
app: app.vera.prod
runs: [216, 217]
category: anti-automation
status: fixed-in-crawler
---
# Vera (app.vera.prod): black screenshots and a misleading integrity screen

**What we saw.** From the first frame the app showed an integrity-check screen ("Entwickler einstellungen öffnen" retry button, "Brauchst du Hilfe?" help toggle, a BSI info button, no skip). Screenshots taken over ADB were black (run 216 step 1; run 217 all 7 frames: about 0.2% bright pixels, only the Samsung edge-panel handle). The accessibility tree (Portal) still returned 19-24 nodes, so the screen could be read but not seen.

**Evidence.** `output_data/run_216_20261004_110624/screenshots/step_0001.png` (black), `reports/crawler_trace.jsonl` (Manager reading the integrity screen from the a11y tree); run 217 console log 12:42-12:45, 8 steps of probing the screen. OmniParser (Replicate) failed on every black frame with `'NoneType' object is not iterable`.

**Cause.** The on-screen text said Developer Options must be turned off. The user found the device actually had **no screen-lock PIN**; the message names the wrong condition. Whether the black capture is FLAG_SECURE or the integrity layer drawing nothing was not established.

**Impact on the crawl.** No coverage: an LLM agent given the screen followed the app's instructions, opened Android Settings (via the retry button) and in run 216 toggled Developer Options off, which dropped the wireless ADB connection and left the run `RUNNING`.

**What the crawler does now** (commits c95fc3d, 2f2587b). A black first capture, or three in a row, stops the run with a "blocks screen capture" message; a black frame in between skips OmniParser; the Settings app in the foreground sends the target app back at once; the goal forbids touching device settings; a lost ADB link fails the run. Not yet re-run on the phone after the PIN was set.
