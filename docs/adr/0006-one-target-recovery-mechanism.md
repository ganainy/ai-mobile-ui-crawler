---
author: claude
---
# One Target Recovery mechanism, not two

Two independent implementations of the same idea — force-relaunch the target app when the device's foreground app isn't it — existed side by side: `AndroidStateProvider._ensure_target_package_active` (`tools/ui/provider.py`, runs before each screenshot/OmniParser capture) and `context_guard.DeviceContextCapture` + `AppSwitchRecovery` (wired into `CrawlerAgentService`, ran after every executed action). Three separate incidents (a browser login, a permission dialog, Google Sign-In) were each fixed by adding an exception to the first mechanism; none of those fixes touched the second, which had no exceptions at all and, after three failed relaunch attempts, raised `FatalError` and aborted the whole run. A crawl could clear the first guard's grace only to be killed by the second on the very next action.

`AppSwitchRecovery`/`DeviceContextCapture` are removed. `_ensure_target_package_active` is now the only place foreground identity is checked, and its policy is inverted: every foreign foreground — a browser, a WebView, an unrecognized app, an unresolvable (`None`) read — gets one default grace period before recovery fires, rather than an allowlist of known-safe packages with zero grace for everything else. `com.google.android.gms` keeps unlimited grace (Google Sign-In's duration is genuinely unbounded). `UIDumpValidator` (a distinct, unrelated concern — validates UI dump shape, not app identity) stays in `context_guard.py`.

## Considered options

- **Fix both mechanisms in parallel**, keeping each patched to the same policy. Rejected: doubles the surface for the next incident to slip through unpatched, which is exactly how this bug happened.
- **Keep `AppSwitchRecovery`, drop the capture-time guard.** Rejected: the capture-time guard already carried the tuned, incident-derived grace values; `AppSwitchRecovery` had none and its abort-after-3-failures behavior is a harsher failure mode with no upside once the capture-time guard's grace is fixed.
- **Keep an allowlist, add more entries (browsers, WebViews, OEM account pickers) as they're found.** Rejected: this is the pattern that produced three incidents already; a per-app-flow allowlist can never be complete since any package could plausibly host a login.
