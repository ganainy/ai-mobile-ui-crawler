---
generated: partial
---
# mobile_crawler.infrastructure

<!-- summary:start -->
Persistence and device integration: SQLite database and repositories (runs, screens, step logs, AI interactions), migrations, ADB and external service clients.
<!-- summary:end -->

## Modules
- [[code/infrastructure/adb_client|infrastructure.adb_client]] - ADB client wrapper for async command execution.
- [[code/infrastructure/adb_input_handler|infrastructure.adb_input_handler]] - ADB input handler for Android text input.
- [[code/infrastructure/ai_interaction_repository|infrastructure.ai_interaction_repository]] - Repository for managing AI interactions in crawler.db.
- [[code/infrastructure/analysis_bundle|infrastructure.analysis_bundle]] - Analysis Bundle writer: the AI-readable half of a Run Report.
- [[code/infrastructure/app_account_store|infrastructure.app_account_store]] - Per-app-package App Account storage (see CONTEXT.md).
- [[code/infrastructure/app_metadata_resolver|infrastructure.app_metadata_resolver]] - Resolves an installed package's display name and icon.
- [[code/infrastructure/app_web_profile_resolver|infrastructure.app_web_profile_resolver]] - Resolves an App Web Profile: descriptive text about what a target app does.
- [[code/infrastructure/credential_store|infrastructure.credential_store]] - Credential store for encrypting sensitive data.
- [[code/infrastructure/database|infrastructure.database]] - Database management for crawler.db - crawl data storage.
- [[code/infrastructure/device_detection|infrastructure.device_detection]] - Device detection utilities for Android devices using ADB.
- [[code/infrastructure/mobsf_docker|infrastructure.mobsf_docker]] - Docker lifecycle management for the MobSF static-analysis server.
- [[code/infrastructure/mobsf_manager|infrastructure.mobsf_manager]] - MobSF Manager for APK analysis.
- [[code/infrastructure/omniparser_docker|infrastructure.omniparser_docker]] - Docker lifecycle management for the local OmniParser server.
- [[code/infrastructure/run_exporter|infrastructure.run_exporter]] - Run exporter for exporting complete run data to JSON.
- [[code/infrastructure/run_repository|infrastructure.run_repository]] - Repository for managing crawl runs in crawler.db.
- [[code/infrastructure/run_stats_repository|infrastructure.run_stats_repository]] - Repository for managing runtime statistics in crawler.db.
- [[code/infrastructure/screen_repository|infrastructure.screen_repository]] - Repository for managing discovered screens in crawler.db.
- [[code/infrastructure/session_folder_manager|infrastructure.session_folder_manager]] - Session folder management for crawler sessions.
- [[code/infrastructure/step_log_repository|infrastructure.step_log_repository]] - Repository for managing step logs in crawler.db.
- [[code/infrastructure/step_phase_repository|infrastructure.step_phase_repository]] - Repository for managing step phase transitions in crawler.db.
- [[code/infrastructure/telemetry_client|infrastructure.telemetry_client]] - Reads a run's telemetry back from Phoenix or Langfuse, by the run's trace session id.
- [[code/infrastructure/user_config_store|infrastructure.user_config_store]] - Database management for user_config.db - user preferences and settings.
