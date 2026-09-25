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

**Action Batch**:
An ordered group of consecutive actions the Executor performs from one Manager subgoal and one screen capture, instead of one action per step. Only the last action may navigate; the batch ends early on the first failure or when the screen no longer matches what it was planned against, and control returns to the Manager. Counts as one step.
_Avoid_: Macro, compound action, multi-action

**Run Report**:
The single output of reporting on one finished crawl run: a human-readable HTML page plus an Analysis Bundle, produced together by one action (auto at run end if enabled, or manually). Replaces the separate HTML report and JSON export. Lives in the run folder's `reports/`, with the run's other reports (MobSF, config snapshot, crawler trace).
_Avoid_: Export, HTML report, run export

**Analysis Bundle**:
The machine-readable half of a Run Report, meant to be read by an AI to find where the crawler can improve: a compact summary, one line per step (action, AI reasoning, result, timings, screenshot paths), and the full run data with a config snapshot. Screenshots are referenced by path, never embedded.
_Avoid_: Analysis export, run dump

**Stop Reason**:
Why a crawl run ended (e.g. step limit, time limit, user stop, error), recorded on the run. Distinct from run status, which only says whether the run is running, stopped or errored.
_Avoid_: End reason, termination cause

**Status Bar Exclusion**:
The number of pixels cropped from the top of every screenshot, at capture time, before it's used for hashing or AI vision. Calibrated by dragging a line on a live device screenshot in Settings rather than guessing a pixel count blind.
_Avoid_: Top bar height, top bar exclusion, exclude top bar

**Bottom Bar Exclusion**:
The number of pixels cropped from the bottom of every screenshot, at capture time, alongside Status Bar Exclusion. Covers the Android navigation bar (3-button nav); defaults to 0 since gesture-navigation devices have none to exclude. Calibrated the same way as Status Bar Exclusion, via a second draggable line on the same preview.
_Avoid_: Bottom bar height, nav bar exclusion, exclude bottom bar

**App Account**:
The login identity (username or email, password, and an optional email address override) belonging to one target app package. Stored per package with no global fallback: an account only means something inside the app it was created for. Replaces the single global "test credentials" set.
_Avoid_: Test credentials, app credentials

**Form Fill Data**:
Generic, app-independent values (address, email, phone) the crawler types into forms that are not a login. Unlike an App Account it is global.
_Avoid_: Test credentials

**Verification Challenge**:
A step in sign-up or login that requires proof of control of an email address or phone number, such as an emailed code or link or an SMS one-time password. The crawler tries to solve it automatically first; when it can't and human fallback is enabled, it asks the user.
_Avoid_: OTP step, verification step, 2FA

**Portal**:
The app installed on the target device whose accessibility service supplies the accessibility tree (element bounds, text, clickable flags) that the crawler reads instead of, or before, running OmniParser. Installed and enabled from Settings, the pre-run dialog's "Enable Portal and start" or the CLI's `a11y-portal enable`, never without being asked; the crawler reads it over adb, so the Portal app's Mobilerun sign-in, API key, IP and token are not needed. Without it, boost mode uses OmniParser only and accessibility mode reports an error.
_Avoid_: Accessibility app, helper app

**Incomplete Accessibility Tree**:
An accessibility tree that boost mode does not trust because it is missing, too small, mostly a WebView/Flutter/game surface, text-only, has too few interactive nodes, or leaves much of the screen uncovered. Only then does boost mode run OmniParser. The checks that fired are logged.
_Avoid_: Sparse tree, weak a11y

**Live Feed**:
A real-time, read-only video view of the selected device's screen, shown in the Stats panel's device board so the user can watch the crawl as it happens. The parsed-element boxes from the latest capture are drawn over it and fade out, since they describe a past snapshot. When the feed is off or unavailable, the board falls back to the last captured screenshot with its boxes. Distinct from the per-step screenshots the crawler captures for its own use and from the recorded run video: the Live Feed is for the human only, and toggled on or off by the user.
_Avoid_: Mirror, screen mirroring, stream

**Human Fallback**:
An opt-in (checkbox) behaviour where, when the crawler cannot solve a Verification Challenge or complete sign-in by itself, it pauses and asks the user to supply the code or finish the step. Times out after a configurable wait, after which authentication is skipped and the crawl continues with whatever is reachable. When off, authentication is skipped immediately on failure.
_Avoid_: Manual mode, human in the loop

**Screen**:
One distinct visual state of the app, identified by a perceptual hash (dHash) of a decision's screenshot; two screenshots within a small hash distance are the same Screen, so a form with different text typed in stays one Screen. Each step records the Screen it started on and the Screen it led to. Screens belong to one app and are shared across that app's runs (a screenshot never matches another app's Screen); "unique screens" counts the distinct Screens one run visited.
_Avoid_: Page, view, state

**Run Stats**:
The statistics saved for one run when it ends (steps, actions, screens, AI calls, recovery, capture sizes), collected from the crawl's events the same way whichever front end (GUI or CLI) started it, and shown by "View Stats" and `stats RUN_ID`.
_Avoid_: Metrics, run summary

**Pre-run Warning**:
A problem found just before a crawl starts that makes it worse than the settings promise (Portal's accessibility service off in boost/accessibility mode, Phoenix tracing on but its Managed Service could not be started). The GUI shows it in a dialog asking whether to start anyway (with "Enable Portal and start" when Portal is installed but off); the CLI prints it to stderr, with the `a11y-portal enable` command for Portal problems, and starts. A Portal problem in accessibility mode _blocks the run_: the crawl would fail at its first step, so the GUI offers only the fix or Cancel and the CLI exits 1 without starting.
_Avoid_: Preflight error, validation error

**Managed Service**:
A local server the app runs in Docker when a feature needs it (MobSF for static analysis, OmniParser for screen parsing, Phoenix for tracing). The app starts it when that feature is on, reuses one already answering at the configured local address instead of starting a second, and never manages one at a remote address. The CLI leaves it running; the GUI offers to stop it on exit.
_Avoid_: Docker container, backend, sidecar
