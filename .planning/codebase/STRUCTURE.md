# Codebase Structure

**Analysis Date:** 2026-04-05

## Directory Layout

```
src/
├── mobile_crawler/
│   ├── cli/                    # Command Line Interface
│   │   ├── __init__.py
│   │   ├── main.py             # CLI entry point
│   │   └── commands/           # Individual CLI commands
│   │       ├── config.py       # Config management
│   │       ├── crawl.py        # Start/stop crawling
│   │       ├── delete.py       # Clean up runs
│   │       ├── list.py         # List runs
│   │       └── report.py       # Generate reports
│   ├── config/                 # Configuration Management
│   │   ├── __init__.py
│   │   ├── config_manager.py   # Central configuration
│   │   ├── defaults.py         # Default values
│   │   └── paths.py           # Path utilities
│   ├── core/                   # Core Application Logic
│   │   ├── __init__.py
│   │   ├── crawl_controller.py     # Pause/resume/stop control
│   │   ├── crawler_event_listener.py
│   │   ├── crawler_loop.py        # DroidRun integration
│   │   ├── crawl_state_machine.py
│   │   ├── logging_service.py      # Central logging
│   │   ├── log_sinks.py
│   │   ├── pre_crawl_validator.py
│   │   ├── runtime_stats_collector.py
│   │   ├── stale_run_cleaner.py
│   │   └── stuck_detector.py
│   ├── domain/                 # Domain Logic Layer
│   │   ├── __init__.py
│   │   ├── action_executor.py      # Action execution abstraction
│   │   ├── adb_action_executor.py  # ADB backend
│   │   ├── app_context_manager.py
│   │   ├── droidrun_agent_service.py # DroidRun integration
│   │   ├── exploration_journal.py
│   │   ├── grounding/             # Grounding for AI decisions
│   │   │   ├── __init__.py
│   │   │   ├── dtos.py
│   │   │   ├── interfaces.py
│   │   │   ├── manager.py
│   │   │   ├── mapper.py
│   │   │   ├── ocr_engine.py
│   │   │   └── overlay.py
│   │   ├── models.py           # Domain models
│   │   ├── model_adapters.py   # Type adapters
│   │   ├── overlay_renderer.py
│   │   ├── prompt_builder.py
│   │   ├── prompts.py
│   │   ├── providers/           # AI provider adapters
│   │   │   ├── gemini_adapter.py
│   │   │   ├── mock_adapter.py
│   │   │   ├── ollama_adapter.py
│   │   │   ├── openrouter_adapter.py
│   │   │   ├── registry.py
│   │   │   └── vision_detector.py
│   │   ├── report_generator.py
│   │   ├── screen_state_manager.py
│   │   ├── screen_tracker.py
│   │   ├── traffic_capture_manager.py
│   │   └── video_recording_manager.py
│   └── infrastructure/        # External Systems
│       ├── __init__.py
│       ├── adb_client.py           # ADB protocol client
│       ├── adb_input_handler.py
│       ├── ai_interaction_repository.py
│       ├── ai_interaction_service.py
│       ├── appium_driver.py        # Appium driver wrapper
│       ├── capability_builder.py
│       ├── credential_store.py
│       ├── database.py            # SQLite management
│       ├── device_detection.py     # USB/ADB device discovery
│       ├── gesture_handler.py
│       ├── mailosaur/             # Email verification service
│       ├── mobsf_manager.py        # MobSF integration
│       ├── run_exporter.py
│       ├── run_repository.py       # Run data access
│       ├── screen_repository.py    # Screen data access
│       ├── screenshot_capture.py
│       ├── session_folder_manager.py
│       ├── step_log_repository.py
│       └── user_config_store.py
```

## Directory Purposes

**CLI Layer (`src/mobile_crawler/cli/`):**
- Purpose: User-facing command-line interface
- Contains: Command definitions and argument parsing
- Key files: `main.py` (entry point), `commands/crawl.py` (crawl execution)

**Config Layer (`src/mobile_crawler/config/`):**
- Purpose: Application configuration management
- Contains: Default values, path resolution, and settings cascade
- Key files: `config_manager.py` (central), `defaults.py` (values)

**Core Layer (`src/mobile_crawler/core/`):**
- Purpose: Application orchestration and coordination
- Contains: Crawl lifecycle management and event system
- Key files: `crawl_controller.py` (state), `crawler_loop.py` (loop)

**Domain Layer (`src/mobile_crawler/domain/`):**
- Purpose: Business logic and AI-driven exploration
- Contains: Action execution, AI agents, and domain models
- Key files: `droidrun_agent_service.py` (AI), `models.py` (entities)

**Infrastructure Layer (`src/mobile_crawler/infrastructure/`):**
- Purpose: External system integration and data persistence
- Contains: Device control, database, and external services
- Key files: `run_repository.py` (data), `adb_client.py` (device)

## Key File Locations

**Entry Points:**
- `src/mobile_crawler/cli/main.py`: CLI application entry
- `src/mobile_crawler/cli/commands/crawl.py`: Crawl execution
- `src/mobile_crawler/core/crawler_loop.py`: Main crawl loop

**Configuration:**
- `src/mobile_crawler/config/config_manager.py`: Central configuration
- `src/mobile_crawler/config/defaults.py`: Default settings

**Core Logic:**
- `src/mobile_crawler/domain/droidrun_agent_service.py`: AI integration
- `src/mobile_crawler/domain/action_executor.py`: Action execution
- `src/mobile_crawler/core/crawl_controller.py`: State management

**Testing:**
- `tests/`: Test directory (structure not explored)

## Naming Conventions

**Files:**
- Lowercase with underscores: `crawl_controller.py`
- Groups in subdirectories: `commands/crawl.py`

**Classes:**
- PascalCase: `CrawlController`, `DroidRunAgentService`
- Descriptive and purposeful: `ActionExecutor`, `RunRepository`

**Methods:**
- Snake_case: `get_run_by_id()`, `should_continue()`
- Clear verbs: `start()`, `stop()`, `pause()`, `resume()`

**Variables:**
- Snake_case: `current_run_id`, `session_path`
- Type hints throughout codebase

## Where to Add New Code

**New Crawl Feature:**
- Primary code: `src/mobile_crawler/domain/`
- Tests: `tests/`
- Configuration: `src/mobile_crawler/config/defaults.py`

**New Command:**
- Implementation: `src/mobile_crawler/cli/commands/new_command.py`
- Register: `src/mobile_crawler/cli/main.py`

**New AI Provider:**
- Implementation: `src/mobile_crawler/domain/providers/new_provider.py`
- Register: `src/mobile_crawler/domain/providers/registry.py`

**New External Service:**
- Implementation: `src/mobile_crawler/infrastructure/new_service.py`
- Configuration: `src/mobile_crawler/config/defaults.py`

## Special Directories

**`src/mobile_crawler/domain/grounding/`:**
- Purpose: AI decision grounding and OCR processing
- Generated: No
- Committed: Yes

**`src/mobile_crawler/infrastructure/mailosaur/`:**
- Purpose: Email verification service integration
- Generated: No
- Committed: Yes

**`src/mobile_crawler/domain/providers/`:**
- Purpose: AI model provider adapters
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-04-05*