---
author: claude
---
# Download a pinned Portal release at setup time instead of vendoring it

The accessibility tree comes from Mobilerun Portal, an app the device runs as an accessibility service (`com.mobilerun.portal`, formerly droidrun-portal). Portal is AGPL-3.0, so committing its APK to this repo would mean redistributing AGPL software (license text, source offer, possible effects on how this project is licensed). Instead `portal.py` downloads one pinned release (`PORTAL_VERSION`) from upstream's GitHub releases when the user clicks "Install / enable Portal" in Settings, verifies it against a pinned SHA-256 (`PORTAL_APK_SHA256`, published in the release's `latest.json`), and caches it in the app data dir.

The cost is that first-time setup needs internet, and upgrading Portal is a deliberate edit of two constants together. Upstream has already renamed itself once (package, repo and content URIs all changed), so the pin is also what keeps a surprise rename from breaking installs.

## Considered options

- **Vendor the APK in the repo** (as done for the scrcpy server, ADR 0004, which is Apache-2.0). Reproducible and offline, but redistributes AGPL software. Rejected.
- **Download the latest release** (the old `portal.py` behaviour). No pin, so an upstream format change could break the client silently. Rejected.
- **`uiautomator dump` over ADB instead of Portal.** No third-party dependency and no install on the device, but measured about 2.3 s per read versus about 1.3 s for Portal, with fewer fields. Kept as the fallback if Portal becomes unmaintainable.
