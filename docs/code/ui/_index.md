---
generated: partial
---
# mobile_crawler.ui

<!-- summary:start -->
PySide6 desktop interface: main window and widgets for device/app selection, live crawl progress, AI monitor, run history, settings.
<!-- summary:end -->

## Modules
- [[code/ui/async_utils|ui.async_utils]] - Utilities for asynchronous operations in the UI.
- [[code/ui/human_fallback_dialog|ui.human_fallback_dialog]] - Qt bridge for Human Fallback: shows a non-blocking dialog on the GUI thread.
- [[code/ui/live_feed_worker|ui.live_feed_worker]] - Background thread that feeds the Live Feed board with decoded device frames.
- [[code/ui/log_cleaner|ui.log_cleaner]] - Log message cleaning: strips ANSI codes, deduplicates, suppresses noise.
- [[code/ui/main_window|ui.main_window]] - Main window for the mobile-crawler GUI application.
- [[code/ui/mobsf_startup_worker|ui.mobsf_startup_worker]] - Background worker that ensures MobSF is running at GUI startup.
- [[code/ui/omniparser_startup_worker|ui.omniparser_startup_worker]] - Background worker that ensures the local OmniParser server is running at GUI startup.
- [[code/ui/portal_actions|ui.portal_actions]] - Blocking Portal check / install helpers for the Settings panel (run them off the UI thread).
- [[code/ui/resources/_index|ui.resources]] - UI resources package.
- [[code/ui/signal_adapter|ui.signal_adapter]] - Qt signal adapter for bridging core events to GUI.
