---
author: claude
---
# UI element detection: modes and options

Question: which modes detect UI elements, do they work, and what could be better.

## Findings
- `ui_parser_mode`: `accessibility` (a11y tree only), `omniparser` (vision only, a11y fetched but ignored), `boost` (a11y if >= 5 elements, else OmniParser). Sources are exclusive per screen; `indexed_formatter.py` uses OmniParser output only when a11y has fewer than 5 elements.
- OCR was dead code, removed in 0c84a7e (see [session](2026-09-20-remove-ocr.md)).
- Settings inconsistency: the combo defaults to `boost`, but the stored default in `settings_panel.py` loads `omniparser`.

## Options discussed (nothing implemented)
- Merge a11y + OmniParser: a11y as base, add OmniParser elements with low IoU against a11y boxes, tag by source. Cost is OmniParser time, so run it only when a11y looks incomplete (few clickables, WebView/Flutter root, uncovered screen area).
- UI-TARS / ShowUI: grounding models (instruction -> coordinates), not enumerators. Possible fallback for failed taps; GPU is an RTX 5070 (12 GB). Model versions and benchmarks not verified.

## Open questions for the user
- What fails today (missed elements, wrong boxes, slowness)?
- When should OmniParser run alongside a11y?
- Fallback grounding model or not?

## Decisions (user, later in the session)
- Text fragmentation: leave as is. Merge a11y + OmniParser only when a11y looks incomplete (WebView/Flutter surface, < 3 clickables, > 40% uncovered area, text-only nodes, plus the existing < 5 rule); config-only, log which check fired. No third (Gemini/Qwen-VL) parser mode now; no local models. Reuse the previous parse for an identical screenshot in both modes. Make `boost` the default in the Settings fallback too.

## Resize benchmark (throwaway, one screen)
- Local Docker OmniParser runs on the GPU (`--device cuda`). One 1080x2400 screen, 27 elements: ~1.1 s at 100% (warm). 50% scale: 89% of boxes matched, 67% same text, 3 clickables lost; 35%: 78% / 62% / 6. The 75% timing was noisy (2.8 s). Fails the agreed bar (95% match, 95% text, no clickable lost, 25% faster): resize looks not worth it.
- The reported ~12 s local average is therefore not explained by the parse call alone on a simple screen; needs a look at per-step `omniparser_ms` on a real run. Only one screen was tested (past run screenshot folders are empty).

## Built (commits 51eb3c0, c67093d)
- Per-capture timing breakdown (guard / keyboard / screenshot / a11y / omniparser / format) logged at INFO and on `ui_state.capture_breakdown_ms`.
- OmniParser parse skipped when the screenshot bytes are identical to the last parse (both modes).

## Finding that changes the plan: there is no accessibility tree
- `AndroidDriver.get_ui_tree()` (the only driver the crawler builds, `droid/crawler_agent.py:408`) always returns `a11y_tree: []` ("Empty - using OmniParser instead", ADB only, no Portal). Portal code (`portal_client.py`, `portal.py`) exists but nothing feeds it into the driver unless `auto_setup` is on, and even then the driver ignores it.
- So `boost` is always OmniParser, and `accessibility` mode yields no elements. The "incomplete a11y" checks and the a11y + OmniParser merge have no a11y data to work on. Plan step 3 is paused; steps 4-5 unaffected.
- Options: (a) uiautomator dump over ADB as a no-install source, (b) revive Portal (accessibility-service APK), (c) drop the a11y modes and simplify to OmniParser only. Could not time `uiautomator dump` because the phone had disconnected.

## Decisions on the a11y source (user: "recommended")
- Revive Portal (not `uiautomator dump`). Setup via an explicit Settings button; `boost` falls back to OmniParser per step when Portal is missing/fails, `accessibility` mode errors instead of returning an empty tree. APK downloaded from upstream at setup time, pinned by version + SHA-256, not vendored (Portal is AGPL-3.0; vendoring means redistributing it). Overlay must be forced off (else OmniParser parses it).

## Portal spike (real phone, Samsung 1080x2400)
- Upstream renamed: repo `droidrun/mobilerun-portal`, package `com.mobilerun.portal` (was `com.droidrun.portal`), service `com.mobilerun.portal/com.mobilerun.portal.service.MobilerunAccessibilityService`, content URI `content://com.mobilerun.portal/...`, asset `com.mobilerun.portal-<ver>.apk`, plus `latest.json` with `versionCode`/`sha256`. Latest v0.7.25 (53 MB, sha256 6dc9e832...3297). `portal.py` still uses the old names.
- `adb install` over wireless succeeded but took minutes.
- `content query --uri content://com.mobilerun.portal/state_full` returns `{a11y_tree (raw nodes: boundsInScreen, isClickable, children, ...), phone_state, device_context}`, i.e. exactly what `AndroidDriver.get_ui_tree` should return. `a11y_tree` (no `_full`) is the compact indexed form without clickable flags.
- Read time ~1.2-1.6 s via `adb shell content query` (a bare `adb shell true` is 0.15-0.3 s), vs `uiautomator dump` ~2.3 s. Portal wins on speed and fields; the HTTP/TCP path might be faster still (not measured).
- Left on the user's phone: Portal installed, its accessibility service enabled (`enabled_accessibility_services` was `null` before), overlay set invisible.

## Built after the spike (commits 2610ff2, effafed)
- `portal.py`: Mobilerun Portal names, pinned v0.7.25 download verified by SHA-256 and cached in `<app data>/portal/`, overlay hidden after setup, read-only `get_portal_status()`. `portal_client.py`: new content URIs.
- `AndroidDriver(use_accessibility=True)` reads `state_full` from Portal; failure leaves an empty tree plus `a11y_error`. `crawler_agent.py` sets it for `boost`/`accessibility`. Provider: accessibility mode raises with the reason if there is no tree; boost threshold counts real nodes (`a11y_completeness.count_nodes`; the root is a dict so `len()` had counted its keys).
- Verified on the phone (launcher screen, boost): source=a11y, 25 elements, OmniParser not called. Capture breakdown: screenshot 2.2-2.7 s, a11y 1.4 s, keyboard 0.15-0.45 s, run one after another over wireless ADB.

## Still to do
- The four "incomplete a11y" checks (surface class, < 3 clickables, > 40% uncovered, text-only) in `a11y_completeness.py`, logged when they trigger OmniParser.
- Settings "Install / enable Portal" button + status (uses `get_portal_status` / `setup_portal`); crawl start should only check and warn.
- `boost` default in the Settings fallback; run screenshot and a11y fetch concurrently (~1.4 s per step); negative phase durations bug; `ui_parser_mode` still defaults to `omniparser` in `config_manager.py`.
