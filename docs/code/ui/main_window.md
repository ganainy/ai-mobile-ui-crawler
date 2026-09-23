---
generated: true
file: src/mobile_crawler/ui/main_window.py
---
# mobile_crawler.ui.main_window

Main window for the mobile-crawler GUI application.

Source: `src/mobile_crawler/ui/main_window.py`

## Classes
- `CrawlStatistics`
- `CrawlerWorker`
- `GuidedScenariosWorker`
- `_ResettableSplitterHandle`
- `PersistedSplitter`
- `MainWindow`

## Functions
- `run`

## Imports
- [[code/config/config_manager|config.config_manager]]
- [[code/config/defaults|config.defaults]]
- [[code/core/crawl_controller|core.crawl_controller]]
- [[code/core/crawl_state_machine|core.crawl_state_machine]]
- [[code/core/crawler_loop|core.crawler_loop]]
- [[code/core/log_sinks|core.log_sinks]]
- [[code/core/portal_actions|core.portal_actions]]
- [[code/core/pre_run_warnings|core.pre_run_warnings]]
- [[code/core/stale_run_cleaner|core.stale_run_cleaner]]
- [[code/domain/guided_scenarios_generator|domain.guided_scenarios_generator]]
- [[code/domain/models|domain.models]]
- [[code/domain/providers/registry|domain.providers.registry]]
- [[code/domain/providers/vision_detector|domain.providers.vision_detector]]
- [[code/domain/report_generator|domain.report_generator]]
- [[code/infrastructure/ai_interaction_repository|infrastructure.ai_interaction_repository]]
- [[code/infrastructure/app_account_store|infrastructure.app_account_store]]
- [[code/infrastructure/database|infrastructure.database]]
- [[code/infrastructure/device_detection|infrastructure.device_detection]]
- [[code/infrastructure/mobsf_docker|infrastructure.mobsf_docker]]
- [[code/infrastructure/mobsf_manager|infrastructure.mobsf_manager]]
- [[code/infrastructure/omniparser_docker|infrastructure.omniparser_docker]]
- [[code/infrastructure/run_repository|infrastructure.run_repository]]
- [[code/infrastructure/run_stats_repository|infrastructure.run_stats_repository]]
- [[code/infrastructure/screen_repository|infrastructure.screen_repository]]
- [[code/infrastructure/session_folder_manager|infrastructure.session_folder_manager]]
- [[code/infrastructure/step_log_repository|infrastructure.step_log_repository]]
- [[code/infrastructure/step_phase_repository|infrastructure.step_phase_repository]]
- [[code/infrastructure/telemetry_client|infrastructure.telemetry_client]]
- [[code/infrastructure/user_config_store|infrastructure.user_config_store]]
- [[code/ui/human_fallback_dialog|ui.human_fallback_dialog]]
- [[code/ui/live_feed_worker|ui.live_feed_worker]]
- [[code/ui/log_cleaner|ui.log_cleaner]]
- [[code/ui/mobsf_startup_worker|ui.mobsf_startup_worker]]
- [[code/ui/omniparser_startup_worker|ui.omniparser_startup_worker]]
- [[code/ui/signal_adapter|ui.signal_adapter]]
- [[code/ui/widgets/ai_model_selector|ui.widgets.ai_model_selector]]
- [[code/ui/widgets/ai_monitor_panel|ui.widgets.ai_monitor_panel]]
- [[code/ui/widgets/app_selector|ui.widgets.app_selector]]
- [[code/ui/widgets/crawl_control_panel|ui.widgets.crawl_control_panel]]
- [[code/ui/widgets/device_selector|ui.widgets.device_selector]]
- [[code/ui/widgets/log_viewer|ui.widgets.log_viewer]]
- [[code/ui/widgets/run_history_view|ui.widgets.run_history_view]]
- [[code/ui/widgets/settings_panel|ui.widgets.settings_panel]]
- [[code/ui/widgets/stats_dashboard|ui.widgets.stats_dashboard]]
