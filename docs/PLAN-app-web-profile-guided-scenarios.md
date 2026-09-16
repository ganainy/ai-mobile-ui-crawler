# Handover: App Web Profile → generated Guided Scenarios

Status: design settled via grilling + domain-modeling session (2026-09-16). Not yet implemented. Written for a fresh AI/engineer to pick up — no prior context assumed beyond this file, `CONTEXT.md`, and `docs/adr/0003-resolve-app-web-profile-separately-and-defer-scrapling.md`.

## What this is

Before starting a crawl, the user can click "Generate" to auto-populate a new, editable **Guided Scenarios** list (ordered subgoals the crawler must hit before free exploration) from information scraped about the target app off the web — its Play Store listing description, plus optionally its developer website. This replaces guesswork ("explore systematically...") with an app-specific checklist derived from what the app's own store listing/site says it does.

Read `CONTEXT.md` first — it now defines **App Web Profile**, **Web Profile Resolution**, **App Web Profile Cache**, and **Guided Scenarios**. This doc assumes those definitions; don't restate them, just build to them. `docs/adr/0003-...md` explains two deliberate choices you should not second-guess without new evidence: (1) a *sibling* resolver to `AppMetadataResolver`, not an extension of it, and (2) plain `requests` instead of `scrapling` for the website step, with failures logged as a tripwire for revisiting that later.

## Settled decisions (do not re-litigate these)

1. **Sources, layered**: Play Store description (via `google_play_scraper`, already a dependency) is primary. The app's developer website — auto-filled from the Play Store listing's `developerWebsite` field into a user-overridable field in the UI — is scraped as plain-text enrichment via `requests` (no JS rendering). A failed/near-empty website fetch is **logged**, not treated as an error, and resolution proceeds with Play Store text alone.
2. **Extraction**: one LLM call, using whatever model the crawler agent is already configured with (no new model-selection UI), turns the combined text into the ordered Guided Scenarios list. On LLM failure or malformed output: leave the list empty/unchanged and surface a visible warning in the UI — mirror the fallback style already used in `CompositeAppCardProvider` (server → local → empty, never silently garbage).
3. **Caching**: a new on-disk cache holds only the *raw fetched text* (Play Store description + scraped site text) per package, same cache-dir/TTL convention as the existing App Metadata Cache (30-day TTL for network-sourced entries, under `get_app_data_dir()`). The LLM extraction step is never cached — every "Generate" click re-runs it live against the (possibly cached) raw text.
4. **Persistence**: the final Guided Scenarios list — after generation and/or manual edits — and the override website URL persist **per app package**, independent of the raw-text cache's TTL. Reselecting an app later reloads what was last generated/edited for it. This is user-owned state, not a cache entry — it never silently expires.
5. **Generate behavior**: clicking "Generate" always replaces the current list wholesale. No merge-with-manual-edits, no confirmation dialog.
6. **UI**: a new "Guided Scenarios" group box in `settings_panel.py`, near the existing "Exploration Objective" group — a list editor (add/remove/reorder), a "Generate" button, and the override-URL field. `settings_panel.py` currently has **zero knowledge of the selected app package** (confirmed: no `package` references in that file at all) — it must stay a dumb view. Wire "Generate" as a signal the panel emits; `main_window.py` (which already owns `self._selected_package`, see below) handles the actual resolve → extract → push-back-into-panel orchestration.

## Existing code this plugs into (exact anchors)

- `src/mobile_crawler/infrastructure/app_metadata_resolver.py` — the pattern to mirror for the new resolver: `_cache_get`/`_cache_put`/`_load_index`/`_save_index` against a JSON index file, `_NETWORK_CACHE_TTL = timedelta(days=30)`, cache dir via `get_app_data_dir()` (`src/mobile_crawler/config/paths.py`). Do **not** modify this file — build a sibling (see ADR 0003).
- `src/mobile_crawler/domain/crawler_agent/app_cards/providers/composite_provider.py` — the fallback style to mirror for the extraction step (try → fall back → empty, logged at each step, never raise).
- `src/mobile_crawler/domain/crawler_agent_service.py:1330-1367` (`_create_exploration_goal`) — line 1343 currently reads `guided = self.config_manager.get("guided_scenarios", [])`, a single **global** config list. This is the one required change to existing logic: swap that line for a lookup of the *new per-package persisted store*, keyed by the `app_package` parameter this method already receives. Everything from line 1344 onward (the prompt-string assembly, the guided/objective merge) is correct as-is and needs no changes.
- `src/mobile_crawler/ui/widgets/settings_panel.py`:
  - Lines ~301-360: existing "Exploration Objective" group box (`objective_group`, `exploration_objective_input`, `reset_objective_button`) — put the new "Guided Scenarios" group box near this one, same visual style.
  - Line 1337 (`get_exploration_objective`) — add analogous `get_guided_scenarios() -> list[str]` and `set_guided_scenarios(list[str])` methods, plus getters/setters for the override URL field.
  - This file has no `package` awareness today — don't add resolver/LLM calls here; expose a `Signal` (e.g. `generate_guided_scenarios_requested`) and let `main_window.py` drive it.
- `src/mobile_crawler/ui/main_window.py`:
  - Line 318 `self._selected_package = None`, line 1444 `_on_app_selected` sets it — this is where you load the persisted Guided Scenarios list + override URL for the newly-selected package into `settings_panel` (via the setters above).
  - Line 712 `exploration_objective = self.settings_panel.get_exploration_objective()`, line 757 `app_package=self._selected_package` — this is the existing call into `execute_exploration_task`; no change needed here since `_create_exploration_goal` will look up the guided list itself by `app_package`.
  - Connect the new `generate_guided_scenarios_requested` signal here: on fire, resolve the App Web Profile (cache-then-network) for `self._selected_package`, run the LLM extraction, call `settings_panel.set_guided_scenarios(...)`, and persist the result.
- `pyproject.toml` — `requests>=2.31.0` and `google-play-scraper>=1.2.0` are already present; **no new dependency is needed** for this feature (scrapling explicitly deferred per ADR 0003).

## Not yet settled — use judgment, don't ask the user again for these

These are implementation-detail choices deliberately left open; pick something reasonable and consistent with the codebase, don't block on them:

- Exact class/file names for the new resolver and the two on-disk stores (raw-text cache vs. persisted Guided-Scenarios+URL state — these are two *different* stores with different lifecycles per decision 3 vs. 4 above; don't collapse them into one file/TTL).
- Exact JSON schema for the persisted per-package store.
- Exact LLM prompt text for the extraction call (combined Play Store + site text → ordered list). Keep it a single call, ask for a strict/parseable output shape (e.g. JSON array of strings) so malformed-output detection (decision 2) is actually checkable.
- Exact HTML-to-text extraction approach for the website fetch (e.g. strip via a lightweight parser already available, or `requests` + basic tag-stripping) — keep it dependency-light, consistent with "plain requests, no JS rendering."
- Exact list-editor widget (Qt list widget with up/down buttons vs. drag-to-reorder) for the Guided Scenarios group box.

## Testing

This repo has both `tests/domain/` and `tests/ui/` with per-file tests (e.g. `test_android_driver_screenshot.py`, `test_app_selector.py`) — follow that convention: a `tests/domain/test_<new_resolver>.py` for the resolver/cache (mock the network calls, verify TTL/cache-key behavior against `AppMetadataResolver`'s existing test if one exists), and a `tests/ui/test_settings_panel.py`-style test (or extend if one exists) for the new getters/setters and signal wiring.
