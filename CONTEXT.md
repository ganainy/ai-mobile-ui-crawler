# Mobile Crawler

An AI-powered Android exploration tool: connects to a device over ADB, picks an installed app, and drives an autonomous crawl of it.

## Language

**App Metadata**:
The resolved display name and icon for a package, as opposed to the raw package id (e.g. `com.alibaba.aliexpresshd`). Shown in the app picker so users recognize apps by name/icon instead of package string.
_Avoid_: App info, app details

**Local Resolution**:
Resolving App Metadata by pulling the installed app's APK from the connected device and parsing it (via `androguard`) for its label and icon. Primary source for apps in the picker, since they're confirmed installed on that device.
_Avoid_: On-device lookup, APK parsing

**Network Resolution**:
Resolving App Metadata by looking up the package name against the Play Store (via `google-play-scraper`) when Local Resolution fails or is unavailable. Fallback only, not primary — package names are treated as non-sensitive for this lookup.
_Avoid_: Online lookup, Play Store lookup

**App Metadata Cache**:
Filesystem cache of resolved App Metadata (icon files + a JSON index) so repeat app-list fetches don't re-resolve every package. Entries from Local Resolution are keyed by package + versionCode (invalidated on app update); entries from Network Resolution have no version signal and are keyed by package name alone with a 30-day refresh.
_Avoid_: Icon cache

**App Web Profile**:
The combined descriptive text for a target app — its Play Store listing description plus, when reachable, text scraped from its developer website — used to generate Guided Scenarios. Distinct from App Metadata (display label/icon) and from an App Card (hand-authored operating instructions): an App Web Profile is scraped source material, not something shown to the user or given to the agent directly.
_Avoid_: App info, app profile, app description

**Web Profile Resolution**:
Fetching an App Web Profile for a package: the Play Store description is fetched first, then the developer website it names (or a user-supplied override) is scraped as plain text enrichment — never JS-rendered, and a failed scrape is logged, not treated as an error.
_Avoid_: Web scraping, app research

**App Web Profile Cache**:
Filesystem cache of resolved App Web Profile text, keyed by package, with the same 30-day refresh convention as the App Metadata Cache's Network Resolution entries. Caches only the raw fetched text — the Guided Scenarios generated from it are never cached, so regenerating after an edit always works from fresh text.
_Avoid_: Web profile cache, scrape cache

**Guided Scenarios**:
An ordered list of subgoals the crawler must complete before it moves to free-form exploration. Persisted per app package; can be generated from that app's App Web Profile with one LLM call, or edited by hand — generating replaces the list wholesale rather than merging with existing entries.
_Avoid_: Guided subgoals, exploration checklist

**Status Bar Exclusion**:
The number of pixels cropped from the top of every screenshot, at capture time, before it's used for hashing, OCR grounding, or AI vision. Calibrated by dragging a line on a live device screenshot in Settings rather than guessing a pixel count blind.
_Avoid_: Top bar height, top bar exclusion, exclude top bar

**Bottom Bar Exclusion**:
The number of pixels cropped from the bottom of every screenshot, at capture time, alongside Status Bar Exclusion. Covers the Android navigation bar (3-button nav); defaults to 0 since gesture-navigation devices have none to exclude. Calibrated the same way as Status Bar Exclusion, via a second draggable line on the same preview.
_Avoid_: Bottom bar height, nav bar exclusion, exclude bottom bar
