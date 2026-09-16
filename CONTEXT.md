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

**Status Bar Exclusion**:
The number of pixels cropped from the top of every screenshot, at capture time, before it's used for hashing, OCR grounding, or AI vision. Calibrated by dragging a line on a live device screenshot in Settings rather than guessing a pixel count blind.
_Avoid_: Top bar height, top bar exclusion, exclude top bar

**Bottom Bar Exclusion**:
The number of pixels cropped from the bottom of every screenshot, at capture time, alongside Status Bar Exclusion. Covers the Android navigation bar (3-button nav); defaults to 0 since gesture-navigation devices have none to exclude. Calibrated the same way as Status Bar Exclusion, via a second draggable line on the same preview.
_Avoid_: Bottom bar height, nav bar exclusion, exclude bottom bar
