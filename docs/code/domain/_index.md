---
generated: partial
---
# mobile_crawler.domain

<!-- summary:start -->
Exploration logic: action execution/verification, screen and state tracking, OCR/Set-of-Mark grounding, model providers, prompts, guided scenarios, traffic/video capture.
<!-- summary:end -->

## Modules
- [[code/domain/action_verifier|domain.action_verifier]] - Post-action verification for UI state transitions.
- [[code/domain/adb_action_executor|domain.adb_action_executor]] - ADB-based action executor for mobile crawler.
- [[code/domain/context_guard|domain.context_guard]] - Device context capture and UI dump validation module for crawl step guardrails.
- [[code/domain/crawler_agent/_index|domain.crawler_agent]] - Droidrun - A framework for controlling Android devices through LLM agents.
- [[code/domain/crawler_agent_service|domain.crawler_agent_service]] - Internal crawler-agent service integration for Mobile Crawler.
- [[code/domain/element_overlay_renderer|domain.element_overlay_renderer]] - Element overlay renderer for UI element labels on screenshots.
- [[code/domain/errors|domain.errors]] - Typed exception taxonomy for the mobile crawler.
- [[code/domain/exploration_journal|domain.exploration_journal]] - Exploration journal for tracking crawl history.
- [[code/domain/grounding/_index|domain.grounding]] - Grounding module for visual interaction mapping.
- [[code/domain/guided_scenarios_generator|domain.guided_scenarios_generator]] - Generates a Guided Scenarios list for an app from its App Web Profile.
- [[code/domain/input_dictionary|domain.input_dictionary]] - Context-aware form input dictionary for matching UI fields to appropriate test values.
- [[code/domain/model_adapters|domain.model_adapters]] - Abstract base class for AI model adapters.
- [[code/domain/models|domain.models]] - Domain models for the mobile crawler.
- [[code/domain/omni_parser_client|domain.omni_parser_client]] - OmniParser client for vision-based UI parsing.
- [[code/domain/omniparser_warmup|domain.omniparser_warmup]] - Warm-up helper for the OmniParser backend.
- [[code/domain/overlay_renderer|domain.overlay_renderer]] - Coordinate overlay rendering for mobile-crawler screenshots.
- [[code/domain/prompt_builder|domain.prompt_builder]] - Prompt builder for AI interactions.
- [[code/domain/prompts|domain.prompts]] - Default prompts for AI interactions.
- [[code/domain/report_generator|domain.report_generator]] - Enhanced HTML/JSON report generator for crawl runs.
- [[code/domain/run_config_snapshot|domain.run_config_snapshot]] - Config snapshot captured at run start, so runs can be compared across crawler changes.
- [[code/domain/run_outcome|domain.run_outcome]] - Derives the Stop Reason and guided-scenario progress recorded on a finished run.
- [[code/domain/screen_hash|domain.screen_hash]] - Shared screen hashing utilities.
- [[code/domain/screen_tracker|domain.screen_tracker]] - Screen tracking service for detecting unique and repeated screens.
- [[code/domain/state_graph|domain.state_graph]] - State transition graph and layout hashing for AI crawler navigation.
- [[code/domain/stats_collector_span_processor|domain.stats_collector_span_processor]] - OTel span processor that collects token counts and LLM latency for the stats dashboard.
- [[code/domain/step_phase|domain.step_phase]] - Step phase state machine for managing individual crawl step lifecycle.
- [[code/domain/step_phase_models|domain.step_phase_models]] - Domain models for step phase transitions.
- [[code/domain/traffic_capture_manager|domain.traffic_capture_manager]] - Traffic capture manager for PCAPdroid integration.
- [[code/domain/ui_context|domain.ui_context]] - UI context management with OmniParser fallback.
- [[code/domain/ui_wait_predicate|domain.ui_wait_predicate]] - Explicit wait predicates for UI synchronization.
- [[code/domain/video_recording_manager|domain.video_recording_manager]] - ADB-backed segmented video recording for crawl sessions.
