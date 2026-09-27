---
author: claude
updated: 2026-09-27
---
# Emulator TLS: PCAPdroid CA naming correction

Continuing work from [emulator-tls doc](../emulator-tls.md) and issue #31 (run 201's pcap still encrypted).

## What happened

The user rooted `tls33` and installed the mitm add-on's CA as a system cert (doc step 6), but a screenshot of Settings > Trusted credentials > System showed an entry named **"PCAPdroid CA"**, not "mitmproxy" as the doc's step 6 claimed. This looked like the wrong certificate was installed.

Checked [PCAPdroid's TLS decryption docs](https://emanuele-f.github.io/PCAPdroid/tls_decryption): PCAPdroid's bundled mitm add-on generates a CA at runtime and it appears as "PCAPdroid CA" — the certificate's Subject/CN, independent of the on-disk filename (`mitmproxy-ca-cert.pem`, from the underlying mitmproxy library the add-on wraps). So "PCAPdroid CA" in the trust store is the expected, correct entry; the doc's earlier "mitmproxy" naming was wrong (or specific to an older add-on version).

## Fix

`docs/emulator-tls.md`:
- Step 6's verification line now says to expect "PCAPdroid CA", with the naming explanation and a link to PCAPdroid's docs.
- Added a two-case checklist under "If it still doesn't decrypt" to tell apart the add-on not being active (no decryption line on a connection's Overview tab) from certificate pinning (explicit decryption error, or payload still starting `17 03 03`).
- Added a correction note pointing back to these from the session log's original "mitmproxy" next-steps.

No code changed. Still open: confirm on the actual Wikipedia test capture which of the two cases applies, using the new checklist.
