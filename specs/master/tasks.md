# Task Breakdown: AI-Powered Android Exploration Tool

> **Based on**: `speckit.implementation-plan.md`  
> **Created**: 2026-01-10  
> **Format**: GitHub Issues-ready tasks

---

## Task Format

Each task includes:
- **ID**: `P{phase}.{task}` format
- **Title**: Action-oriented summary
- **Description**: What needs to be done
- **Acceptance Criteria**: Definition of done
- **Dependencies**: Blocking tasks
- **Files**: Expected files to create/modify
- **Estimated Hours**: Time estimate

---

## Phase 0: Project Foundation

### P0.1 — Initialize Python Project Structure

**Description**  
Set up the Python project with modern tooling. Create `pyproject.toml` with dependencies, configure package metadata, and establish the directory structure.

**Acceptance Criteria**
- [X] `pyproject.toml` exists with all dependencies listed
- [X] Project installable with `pip install -e .`
- [X] Directory structure matches spec:
  ```
  src/
  ├── core/
  ├── infrastructure/
  ├── domain/
  ├── ui/
  ├── cli/
  ├── config/
  └── utils/
  ```
- [X] `__init__.py` files in all packages

**Dependencies**: None

**Files**
- `pyproject.toml`
- `src/**/__init__.py`
- `README.md`

**Estimated Hours**: 1.5

---

### P0.2 — Configure Linting and Formatting

**Description**  
Set up Ruff for linting and Black for formatting. Configure pre-commit hooks.

**Acceptance Criteria**
- [X] `ruff check .` passes with no errors
- [X] `black --check .` passes
- [X] `.pre-commit-config.yaml` configured
- [X] VS Code settings for auto-format on save

**Dependencies**: P0.1

**Files**
- `pyproject.toml` (tool sections)
- `.pre-commit-config.yaml`
- `.vscode/settings.json`

**Estimated Hours**: 0.5

---

### P0.3 — Set Up Testing Framework

**Description**  
Configure pytest with fixtures, markers, and coverage reporting.

**Acceptance Criteria**
- [X] `pytest.ini` or `pyproject.toml` [tool.pytest] configured
- [X] `tests/` directory with `conftest.py`
- [X] Sample test passes: `pytest -v` (187 tests passing)
- [X] Coverage report generates: `pytest --cov` (86% coverage)

**Dependencies**: P0.1

**Files**
- `pyproject.toml` (pytest config)
- `tests/conftest.py`
- `tests/test_placeholder.py`

**Estimated Hours**: 1

---

### P0.4 — Implement Logging Infrastructure

**Description**  
Create `LoggingService` with multi-sink architecture: ConsoleSink (stderr), JSONEventSink (stdout), FileSink (crawler.log), DatabaseSink (logs table).

**Acceptance Criteria**
- [X] `LoggingService` class with configurable sinks
- [X] Console output is human-readable, level-filtered
- [X] JSON events go to stdout (for CLI piping)
- [X] File sink writes to `crawler.log` with rotation
- [X] Log levels: DEBUG, INFO, WARNING, ERROR, ACTION
- [X] Unit tests for each sink

**Dependencies**: P0.1

**Files**
- `src/core/logging_service.py`
- `src/core/log_sinks.py`
- `tests/core/test_logging.py`

**Estimated Hours**: 2.5

---

### P0.5 — Implement Configuration System

**Description**  
Create configuration manager with precedence: SQLite → environment variables → module defaults.

**Acceptance Criteria**
- [X] `ConfigManager` class with `get(key)` method
- [X] Precedence order enforced
- [X] Default values defined in `config/defaults.py`
- [X] Environment variable prefix: `CRAWLER_`
- [X] Unit tests for precedence

**Dependencies**: P0.1, P1.2 (partial — can stub DB)

**Files**
- `src/config/config_manager.py`
- `src/config/defaults.py`
- `tests/config/test_config_manager.py`

**Estimated Hours**: 2

---

## Phase 1: Database & Storage Layer

### P1.1 — Create crawler.db Schema

**Description**  
Implement SQLite schema for crawl data: `runs`, `screens`, `step_logs`, `transitions`, `run_stats`, `ai_interactions` tables with indexes.

**Acceptance Criteria**
- [X] All 6 tables created per spec
- [X] Foreign keys enforced
- [X] Indexes created for performance
- [X] Migration script for schema changes
- [X] WAL mode enabled

**Dependencies**: P0.1

**Files**
- `src/infrastructure/database.py`
- `src/infrastructure/migrations/001_initial_schema.sql`
- `tests/infrastructure/test_database.py`

**Estimated Hours**: 2.5

---

### P1.2 — Create user_config.db Schema

**Description**  
Implement SQLite schema for user preferences: `user_config`, `secrets` tables.

**Acceptance Criteria**
- [X] Both tables created per spec
- [X] Key-value storage with type metadata
- [X] Separate DB file from crawler.db
- [X] Unit tests

**Dependencies**: P0.1

**Files**
- `src/infrastructure/user_config_store.py`
- `tests/infrastructure/test_user_config_store.py`

**Estimated Hours**: 1

---

### P1.3 — Implement Secrets Encryption

**Description**  
Implement Fernet encryption for API keys with machine-bound key derivation via PBKDF2.

**Acceptance Criteria**
- [X] `CredentialStore` class with `encrypt()` / `decrypt()`
- [X] Key derived from machine identifier (hostname + MAC)
- [X] Encrypted values stored as BLOB
- [X] Unit tests verify roundtrip

**Dependencies**: P1.2

**Files**
- `src/infrastructure/credential_store.py`
- `tests/infrastructure/test_credential_store.py`

**Estimated Hours**: 2

---

### P1.4 — Implement Run CRUD Operations

**Description**  
Create, read, update, delete operations for `runs` table with cascading deletes to related tables and session folders.

**Acceptance Criteria**
- [X] `RunRepository` with CRUD methods
- [X] `delete_run()` cascades to `step_logs`, `transitions`, `run_stats`, `ai_interactions`
- [X] Session folder deleted with run
- [X] Unit tests for all operations

**Dependencies**: P1.1, P1.7

**Files**
- `src/core/repositories/run_repository.py`
- `tests/core/test_run_repository.py`

**Estimated Hours**: 2

---

### P1.5 — Implement Screen State Storage (Repository Layer)

**Description**  
Database repository layer for screen persistence. Stores and deduplicates screens using perceptual hashing with Hamming distance threshold of 5. This is the **storage layer** (CRUD operations); see P4.4 for domain logic.

**Acceptance Criteria**
- [X] `ScreenRepository` with `find_or_create()`
- [X] Visual hash comparison with threshold
- [X] Composite hash = activity + visual hash
- [X] Unit tests with sample images

**Dependencies**: P1.1

**Files**
- `src/core/repositories/screen_repository.py`
- `tests/core/test_screen_repository.py`
- `tests/core/test_screen_repository.py`

**Estimated Hours**: 2.5

---

### P1.6 — Implement Step Log Storage

**Description**  
Store per-step action history in `step_logs` table.

**Acceptance Criteria**
- [X] `StepLogRepository` with insert/query methods
- [X] `get_exploration_journal(run_id, limit=15)`
- [X] Foreign key references to screens
- [X] Unit tests

**Dependencies**: P1.1, P1.5

**Files**
- `src/core/repositories/step_log_repository.py`
- `tests/core/test_step_log_repository.py`

**Estimated Hours**: 1.5

---

### P1.7 — Implement Session Folder Management

**Description**  
Create/delete `output_data/{device_id}_{app_package}_{DD_MM_HH_MM}/` folders with subdirectories.

**Acceptance Criteria**
- [X] `SessionFolderManager` class
- [X] Creates all subdirectories (screenshots, logs, video, etc.)
- [X] Timestamp format: `DD_MM_HH_MM`
- [X] Delete folder with all contents
- [X] Unit tests

**Dependencies**: P0.1

**Files**
- `src/infrastructure/session_folder_manager.py`
- `tests/infrastructure/test_session_folder_manager.py`

**Estimated Hours**: 1

---

## Phase 2: Appium Integration

### P2.1 — Implement Appium Driver Wrapper

**Description**  
Create `AppiumDriver` class wrapping Appium WebDriver with session management, error handling, and reconnection.

**Acceptance Criteria**
- [X] `AppiumDriver` connects to `localhost:4723`
- [X] Session creation with UiAutomator2 capabilities
- [X] Auto-reconnect on session loss
- [X] Graceful session cleanup
- [X] Integration test with emulator

**Dependencies**: P0.1

**Files**
- `src/infrastructure/appium_driver.py`
- `src/infrastructure/capability_builder.py`
- `tests/infrastructure/test_appium_driver.py`

**Estimated Hours**: 3

---

### P2.2 — Implement Device Detection

**Description**  
List connected Android devices via ADB.

**Acceptance Criteria**
- [X] `DeviceDetector.get_connected_devices()` returns list
- [X] Each device has: id, model, android_version
- [X] Handles no devices gracefully
- [X] Unit tests with mocked ADB output

**Dependencies**: P0.1

**Files**
- `src/infrastructure/device_detection.py`
- `tests/infrastructure/test_device_detection.py`

**Estimated Hours**: 1

---

### P2.3 — Implement Screenshot Capture

**Description**  
Capture screenshots via Appium and downscale to max 1280px.

**Acceptance Criteria**
- [X] `capture_screenshot()` returns PIL Image
- [X] Downscaled preserving aspect ratio
- [X] Saves to session folder as PNG
- [X] Returns path and base64 for AI
- [X] Unit tests

**Dependencies**: P2.1

**Files**
- `src/infrastructure/screenshot_capture.py`
- `tests/infrastructure/test_screenshot_capture.py`

**Estimated Hours**: 1.5

---

### P2.4 — Implement Action Executor

**Description**  
Execute all 8 action types: `click`, `input`, `long_press`, `scroll_up`, `scroll_down`, `swipe_left`, `swipe_right`, `back`.

**Acceptance Criteria**
- [X] `ActionExecutor` class with method per action type
- [X] Bounding box center calculation for tap actions
- [X] Scroll/swipe from screen center
- [X] Returns `ActionResult` dataclass
- [X] 0.5s delay between actions
- [X] Integration tests

**Dependencies**: P2.1, P2.5

**Files**
- `src/domain/action_executor.py`
- `tests/domain/test_action_executor.py`

**Estimated Hours**: 4

---

### P2.5 — Implement Gesture Handler

**Description**  
Calculate coordinates from bounding boxes and execute gestures.

**Acceptance Criteria**
- [X] `GestureHandler` with `tap`, `long_press`, `swipe`, `scroll`, `drag`
- [X] `GestureType` enum for all gesture types
- [X] Center point from bounding box
- [X] Configurable swipe distances
- [X] Fallback to coordinate-based gestures when element not found
- [X] Unit tests (26 tests, 83% coverage)

**Dependencies**: P2.1

**Files**
- `src/infrastructure/gesture_handler.py`
- `tests/infrastructure/test_gesture_handler.py`

**Estimated Hours**: 1

---

### P2.6 — Implement Video Recording Manager

**Description**  
Start/stop screen recording via Appium API, save to session folder.

**Acceptance Criteria**
- [X] `VideoRecordingManager` with `start()`, `stop_and_save()`
- [X] Uses Appium's built-in recording
- [X] Decodes base64 and saves MP4
- [X] Handles partial save on crash
- [X] Integration test

**Dependencies**: P2.1, P1.7

**Files**
- `src/domain/video_recording_manager.py`
- `tests/domain/test_video_recording_manager.py`

**Estimated Hours**: 2

---

### P2.7 — Implement App Context Manager

**Description**  
Detect current package, handle context loss, relaunch app when needed.

**Acceptance Criteria**
- [X] `AppContextManager` tracks current package
- [X] Detects context loss (package not in allowed list)
- [X] Press back up to 3×, then relaunch
- [X] Counts `context_loss_count`, `context_recovery_count`
- [X] Unit tests

**Dependencies**: P2.1

**Files**
- `src/domain/app_context_manager.py`
- `tests/domain/test_app_context_manager.py`

**Estimated Hours**: 2

---

### P2.8 — Implement Element Finder

**Description**  
Parse UiAutomator2 XML hierarchy to extract UI elements with bounds, resource IDs, and accessibility information. Provides precise targeting data for action execution.

**Acceptance Criteria**
- [X] `ElementFinder` class with `find_elements()` returning `List[UIElement]`
- [X] `UIElement` dataclass with 13 fields: element_id, bounds, text, content_desc, class_name, package, clickable, visible, enabled, resource_id, xpath, center_x, center_y
- [X] Parse XML from Appium `page_source`
- [X] Filter elements by visibility, clickability
- [X] Calculate center coordinates from bounds
- [X] Unit tests with sample XML

**Dependencies**: P2.1

**Files**
- `src/mobile_crawler/infrastructure/element_finder.py`
- `src/mobile_crawler/domain/models.py` (UIElement dataclass)
- `tests/infrastructure/test_element_finder.py`

**Estimated Hours**: 2

---

## Phase 3: AI Provider Integration

### P3.1 — Define ModelAdapter Interface

**Description**  
Create abstract base class for AI provider adapters.

**Acceptance Criteria**
- [X] `ModelAdapter` ABC with:
  - `initialize(model_config, safety_settings)`
  - `generate_response(prompt, image) -> (str, dict)`
  - `model_info` property
- [X] Type hints complete
- [X] Docstrings

**Dependencies**: P0.1

**Files**
- `src/domain/model_adapters.py`

**Estimated Hours**: 1

---

### P3.2 — Implement GeminiAdapter

**Description**  
Implement adapter for Google Gemini API.

**Acceptance Criteria**
- [X] `GeminiAdapter` extends `ModelAdapter`
- [X] Uses `google-genai` SDK
- [X] Handles image encoding
- [X] Returns token usage in metadata
- [X] Unit tests with mocked API

**Dependencies**: P3.1

**Files**
- `src/domain/providers/gemini_adapter.py`
- `tests/domain/providers/test_gemini_adapter.py`

**Estimated Hours**: 3

---

### P3.3 — Implement OpenRouterAdapter

**Description**  
Implement adapter for OpenRouter API.

**Acceptance Criteria**
- [X] `OpenRouterAdapter` extends `ModelAdapter`
- [X] HTTP client with proper headers
- [X] Model name normalization
- [X] Token usage extraction
- [X] Unit tests with mocked API

**Dependencies**: P3.1

**Files**
- `src/domain/providers/openrouter_adapter.py`
- `tests/domain/providers/test_openrouter_adapter.py`

**Estimated Hours**: 3

---

### P3.4 — Implement OllamaAdapter

**Description**  
Implement adapter for local Ollama.

**Acceptance Criteria**
- [X] `OllamaAdapter` extends `ModelAdapter`
- [X] Uses `ollama` Python SDK
- [X] Handles local base URL
- [X] Unit tests with mocked client

**Dependencies**: P3.1

**Files**
- `src/domain/providers/ollama_adapter.py`
- `tests/domain/providers/test_ollama_adapter.py`

**Estimated Hours**: 3

---

### P3.5 — Implement Vision Model Detection

**Description**  
Filter models by vision capability for each provider.

**Acceptance Criteria**
- [ ] `ProviderRegistry` fetches available models
- [ ] Filters to vision-capable only
- [ ] Gemini: check model name patterns
- [ ] OpenRouter: check `modalities` metadata
- [ ] Ollama: check for `projector`, `clip`, `vision` in show output
- [ ] Caches results
- [ ] Unit tests

**Dependencies**: P3.2, P3.3, P3.4

**Files**
- `src/domain/providers/registry.py`
- `src/domain/providers/vision_detector.py`
- `tests/domain/providers/test_vision_detector.py`

**Estimated Hours**: 2.5

---

### P3.6 — Implement AI Interaction Service

**Description**  
Build requests, call adapters, parse responses, handle retries.

**Acceptance Criteria**
- [ ] `AIInteractionService` with `get_next_actions(screenshot, journal, is_stuck)`
- [ ] Builds request per spec schema
- [ ] Validates response schema
- [ ] Retry up to 2× on error
- [ ] Logs to `ai_interactions` table
- [ ] Unit tests

**Dependencies**: P3.1, P3.7, P1.1

**Files**
- `src/infrastructure/ai_interaction_service.py`
- `tests/infrastructure/test_ai_interaction_service.py`

**Estimated Hours**: 3

---

### P3.7 — Implement Prompt Builder

**Description**  
Build system prompt with exploration journal and available actions.

**Acceptance Criteria**
- [X] `PromptBuilder` class
- [X] Default system prompt defined
- [X] User can replace fully
- [X] Formats exploration journal (last 15 entries)
- [X] Lists available actions
- [X] Includes test credentials if provided
- [X] Unit tests

**Dependencies**: P0.1

**Files**
- `src/domain/prompt_builder.py`
- `src/domain/prompts.py` (default prompts)
- `tests/domain/test_prompt_builder.py`

**Estimated Hours**: 2

---

## Phase 4: Crawler Core

### P4.1 — Implement Crawl State Machine

**Description**  
Explicit state machine with transitions: UNINITIALIZED → INITIALIZING → RUNNING ⇄ PAUSED_MANUAL → STOPPING → STOPPED / ERROR.

**Acceptance Criteria**
- [X] `CrawlState` enum with all states
- [X] `CrawlStateMachine` with valid transitions
- [X] Invalid transitions raise exception
- [X] State change events emitted
- [X] Unit tests for all transitions

**Dependencies**: P0.4

**Files**
- `src/core/crawl_state_machine.py`
- `tests/core/test_crawl_state_machine.py`

**Estimated Hours**: 2

---

### P4.2 — Implement Crawler Loop

**Description**  
Main iteration: screenshot → AI → execute → log → repeat.

**Acceptance Criteria**
- [ ] `CrawlerLoop` class with `run()`
- [ ] Respects `MAX_CRAWL_STEPS` and `MAX_CRAWL_DURATION_SECONDS`
- [ ] Handles batch abort on failure
- [ ] Emits events via `CrawlerEventListener` protocol
- [ ] Integration test

**Dependencies**: P4.1, P2.3, P2.4, P3.6, P1.6

**Files**
- `src/core/crawler_loop.py`
- `src/core/crawler_event_listener.py`
- `tests/core/test_crawler_loop.py`

**Estimated Hours**: 4

---

### P4.3 — Implement Stuck Detector

**Description**  
Detect when crawler is stuck on same screen consecutively.

**Acceptance Criteria**
- [ ] `StuckDetector` tracks consecutive visits
- [ ] Threshold: >2 consecutive visits
- [ ] Sets `is_stuck=True` and `stuck_reason`
- [ ] Tracks `stuck_recovery_success`
- [ ] Unit tests

**Dependencies**: P1.5

**Files**
- `src/core/stuck_detector.py`
- `tests/core/test_stuck_detector.py`

**Estimated Hours**: 2

---

### P4.4 — Implement Screen State Manager (Domain Logic)

**Description**  
Domain-level screen state detection and management. Handles visual hashing, similarity detection, state transitions (LOADING/READY/ERROR), and visit tracking. This is the **domain logic layer**; see P1.5 for storage persistence.

**Acceptance Criteria**
- [X] `ScreenStateManager` with `detect_screen_state()`, `take_snapshot()`, `wait_for_state()`
- [X] `ScreenState` enum: LOADING, READY, INTERACTING, ERROR, UNKNOWN
- [X] `ScreenSnapshot` dataclass with image, elements, timestamp
- [X] Perceptual hash using imagehash
- [X] Hamming distance ≤ 5 = same screen
- [X] Maintains `visit_counts` per run
- [X] Unit tests (22 tests passing)

**Dependencies**: P1.5, P2.3

**Files**
- `src/domain/screen_state_manager.py`
- `tests/domain/test_screen_state_manager.py`

**Estimated Hours**: 3

---

### P4.5 — Implement Exploration Journal

**Description**  
Query last 15 steps from step_logs for AI context.

**Acceptance Criteria**
- [ ] `ExplorationJournal` with `get_entries(run_id, limit=15)`
- [ ] Returns `JournalEntry` dataclass list
- [ ] Derived from step_logs (no separate storage)
- [ ] Unit tests

**Dependencies**: P1.6

**Files**
- `src/domain/exploration_journal.py`
- `tests/domain/test_exploration_journal.py`

**Estimated Hours**: 1

---

### P4.6 — Implement Runtime Statistics Collector

**Description**  
Track all 60+ metrics during crawl, persist to `run_stats`.

**Acceptance Criteria**
- [ ] `RuntimeStatsCollector` class
- [ ] Tracks all metrics per spec categories
- [ ] JSON storage for dict-type metrics
- [ ] `save()` persists to DB
- [ ] Unit tests

**Dependencies**: P1.1

**Files**
- `src/core/runtime_stats_collector.py`
- `tests/core/test_runtime_stats_collector.py`

**Estimated Hours**: 3

---

### P4.7 — Implement Pause/Resume/Stop Controls

**Description**  
Thread-safe control flags for crawl loop.

**Acceptance Criteria**
- [ ] `CrawlController` with `pause()`, `resume()`, `stop()`
- [ ] Thread-safe flag management
- [ ] Loop checks flags between steps
- [ ] Events emitted on state change
- [ ] Unit tests

**Dependencies**: P4.1

**Files**
- `src/core/crawl_controller.py`
- `tests/core/test_crawl_controller.py`

**Estimated Hours**: 2

---

### P4.8 — Implement Pre-Crawl Validation

**Description**  
Check all requirements before crawl starts.

**Acceptance Criteria**
- [ ] `PreCrawlValidator` with `validate() -> List[ValidationError]`
- [ ] Checks: Appium reachable, device connected, app selected, model selected, API key present
- [ ] Optional checks: MobSF, PCAPdroid, video (warn only)
- [ ] Unit tests

**Dependencies**: P2.1, P2.2, P3.5, P1.3

**Files**
- `src/core/pre_crawl_validator.py`
- `tests/core/test_pre_crawl_validator.py`

**Estimated Hours**: 2

---

## Phase 5: External Integrations

### P5.1 — Implement PCAPdroid Manager

**Description**  
Start/stop traffic capture via intent API, pull PCAP file.

**Acceptance Criteria**
- [ ] `TrafficCaptureManager` with `start()`, `stop_and_pull()`
- [ ] ADB shell commands per spec
- [ ] Pulls file from device to session folder
- [ ] Graceful handling if PCAPdroid not installed
- [ ] Integration test

**Dependencies**: P2.1, P1.7

**Files**
- `src/domain/traffic_capture_manager.py`
- `tests/domain/test_traffic_capture_manager.py`

**Estimated Hours**: 3

---

### P5.2 — Implement MobSF Manager

**Description**  
Extract APK, upload to MobSF, retrieve results.

**Acceptance Criteria**
- [ ] `MobSFManager` with `analyze(package)` 
- [ ] Extracts APK from device via `adb pull`
- [ ] Uploads to MobSF REST API
- [ ] Downloads PDF + JSON results
- [ ] Handles split APKs gracefully (error + continue)
- [ ] Can run on past runs
- [ ] Integration test

**Dependencies**: P2.1, P1.7

**Files**
- `src/infrastructure/mobsf_manager.py`
- `tests/infrastructure/test_mobsf_manager.py`

**Estimated Hours**: 3

---

### P5.3 — Implement PDF Report Generator

**Description**  
Generate PDF report using ReportLab.

**Acceptance Criteria**
- [ ] `ReportGenerator` with `generate(run_id) -> path`
- [ ] Includes: summary stats, action timeline, screen coverage, error summary
- [ ] Works for completed and stopped runs
- [ ] Saves to session folder
- [ ] Unit tests

**Dependencies**: P1.4, P4.6

**Files**
- `src/domain/report_generator.py`
- `tests/domain/test_report_generator.py`

**Estimated Hours**: 4

---

### P5.4 — Implement Stale Run Cleanup

**Description**  
On startup, recover partial artifacts from crashed runs.

**Acceptance Criteria**
- [ ] `StaleRunCleaner` runs on app start
- [ ] Finds runs with status=RUNNING but no process
- [ ] Attempts to stop Appium recording, pull partial video
- [ ] Attempts to stop PCAPdroid, pull partial PCAP
- [ ] Marks run as ERROR
- [ ] Unit tests

**Dependencies**: P1.4, P2.6, P5.1

**Files**
- `src/core/stale_run_cleaner.py`
- `tests/core/test_stale_run_cleaner.py`

**Estimated Hours**: 2

---

## Phase 6: CLI Interface

### P6.1 — Set Up Click Framework

**Description**  
Create CLI entry point with Click.

**Acceptance Criteria**
- [ ] `run_cli.py` entry point
- [ ] `crawler` command group
- [ ] `--version` flag
- [ ] Help text

**Dependencies**: P0.1

**Files**
- `run_cli.py`
- `src/cli/__init__.py`
- `src/cli/main.py`

**Estimated Hours**: 1

---

### P6.2 — Implement `crawl` Command

**Description**  
Start crawl with options for device, package, model, limits.

**Acceptance Criteria**
- [ ] `crawler crawl --device <id> --package <pkg> --model <name>`
- [ ] Optional: `--steps`, `--duration`, `--provider`
- [ ] JSON events to stdout
- [ ] Human logs to stderr
- [ ] Integration test

**Dependencies**: P6.1, P4.2

**Files**
- `src/cli/commands/crawl.py`
- `tests/cli/test_crawl_command.py`

**Estimated Hours**: 2

---

### P6.3 — Implement `config` Commands

**Description**  
Set/get API keys and preferences.

**Acceptance Criteria**
- [ ] `crawler config set <key> <value>`
- [ ] `crawler config get <key>`
- [ ] `crawler config list`
- [ ] Secrets stored encrypted
- [ ] Unit tests

**Dependencies**: P6.1, P1.2, P1.3

**Files**
- `src/cli/commands/config.py`
- `tests/cli/test_config_command.py`

**Estimated Hours**: 2

---

### P6.4 — Implement `report` Command

**Description**  
Generate report for past run.

**Acceptance Criteria**
- [ ] `crawler report <run_id>`
- [ ] Optional: `--output <path>`
- [ ] Works for completed and stopped runs
- [ ] Unit tests

**Dependencies**: P6.1, P5.3

**Files**
- `src/cli/commands/report.py`
- `tests/cli/test_report_command.py`

**Estimated Hours**: 1

---

### P6.5 — Implement `list` Commands

**Description**  
List runs and devices.

**Acceptance Criteria**
- [ ] `crawler list runs` — shows past runs
- [ ] `crawler list devices` — shows connected devices
- [ ] JSON output with `--json` flag
- [ ] Unit tests

**Dependencies**: P6.1, P1.4, P2.2

**Files**
- `src/cli/commands/list.py`
- `tests/cli/test_list_command.py`

**Estimated Hours**: 1

---

### P6.6 — Implement `delete` Command

**Description**  
Delete old runs with cascading cleanup.

**Acceptance Criteria**
- [ ] `crawler delete <run_id>`
- [ ] Confirmation prompt (skip with `--yes`)
- [ ] Deletes DB records and session folder
- [ ] Unit tests

**Dependencies**: P6.1, P1.4

**Files**
- `src/cli/commands/delete.py`
- `tests/cli/test_delete_command.py`

**Estimated Hours**: 1

---

## Phase 7: GUI Interface

### P7.1 — Set Up PySide6 Application

**Description**  
Create main window and application structure.

**Acceptance Criteria**
- [ ] `run_ui.py` entry point
- [ ] `MainWindow` class with menu bar
- [ ] Application icon
- [ ] Closes cleanly

**Dependencies**: P0.1

**Files**
- `run_ui.py`
- `src/ui/__init__.py`
- `src/ui/main_window.py`

**Estimated Hours**: 2

---

### P7.2 — Implement Device Selection Widget

**Description**  
Dropdown with detected devices, refresh button.

**Acceptance Criteria**
- [ ] `DeviceSelector` widget
- [ ] Refresh button updates list
- [ ] Shows device model and ID
- [ ] Emits `device_selected` signal

**Dependencies**: P7.1, P2.2

**Files**
- `src/ui/widgets/device_selector.py`
- `tests/ui/test_device_selector.py`

**Estimated Hours**: 2

---

### P7.3 — Implement App Selection Widget

**Description**  
Package input with validation.

**Acceptance Criteria**
- [ ] `AppSelector` widget with text input
- [ ] Validates package format
- [ ] Optional: list installed apps from device
- [ ] Emits `app_selected` signal

**Dependencies**: P7.1, P2.1

**Files**
- `src/ui/widgets/app_selector.py`
- `tests/ui/test_app_selector.py`

**Estimated Hours**: 1.5

---

### P7.4 — Implement AI Provider/Model Selection

**Description**  
Provider dropdown, model list filtered to vision-capable.

**Acceptance Criteria**
- [ ] `AIModelSelector` widget
- [ ] Provider dropdown (Gemini, OpenRouter, Ollama)
- [ ] Model list updates on provider change
- [ ] Only vision-capable models shown
- [ ] Emits `model_selected` signal

**Dependencies**: P7.1, P3.5

**Files**
- `src/ui/widgets/ai_model_selector.py`
- `tests/ui/test_ai_model_selector.py`

**Estimated Hours**: 3

---

### P7.5 — Implement Crawl Control Panel

**Description**  
Start/Pause/Resume/Stop buttons with state management.

**Acceptance Criteria**
- [ ] `CrawlControlPanel` widget
- [ ] Button states reflect crawl state
- [ ] Start disabled until pre-validation passes
- [ ] Emits control signals

**Dependencies**: P7.1, P4.7

**Files**
- `src/ui/widgets/crawl_control_panel.py`
- `tests/ui/test_crawl_control_panel.py`

**Estimated Hours**: 2

---

### P7.6 — Implement Real-Time Log Viewer

**Description**  
Scrolling log with level filtering.

**Acceptance Criteria**
- [ ] `LogViewer` widget
- [ ] Auto-scroll to bottom
- [ ] Level filter dropdown
- [ ] Color-coded levels
- [ ] Clear button

**Dependencies**: P7.1, P0.4

**Files**
- `src/ui/widgets/log_viewer.py`
- `tests/ui/test_log_viewer.py`

**Estimated Hours**: 2

---

### P7.7 — Implement Statistics Dashboard

**Description**  
Live metrics display during crawl.

**Acceptance Criteria**
- [ ] `StatsDashboard` widget
- [ ] Shows key metrics: steps, screens, errors
- [ ] Updates in real-time
- [ ] Progress bar for step/time limit

**Dependencies**: P7.1, P4.6

**Files**
- `src/ui/widgets/stats_dashboard.py`
- `tests/ui/test_stats_dashboard.py`

**Estimated Hours**: 3

---

### P7.8 — Implement Settings Panel

**Description**  
API keys, system prompt, crawl limits, test credentials.

**Acceptance Criteria**
- [ ] `SettingsPanel` widget
- [ ] API key inputs (masked)
- [ ] System prompt text area (replaceable)
- [ ] Crawl limit inputs
- [ ] Test credentials inputs
- [ ] Save button persists to user_config.db

**Dependencies**: P7.1, P1.2, P1.3

**Files**
- `src/ui/widgets/settings_panel.py`
- `tests/ui/test_settings_panel.py`

**Estimated Hours**: 3

---

### P7.9 — Implement Run History View

**Description**  
List past runs, delete, generate report.

**Acceptance Criteria**
- [ ] `RunHistoryView` widget
- [ ] Table with run metadata
- [ ] Delete button with confirmation
- [ ] Generate Report button (checkbox for optional)
- [ ] Run MobSF button (for past runs)

**Dependencies**: P7.1, P1.4, P5.3

**Files**
- `src/ui/widgets/run_history_view.py`
- `tests/ui/test_run_history_view.py`

**Estimated Hours**: 3

---

### P7.10 — Implement Qt Signal Adapter

**Description**  
Bridge core events to GUI without Qt in core.

**Acceptance Criteria**
- [ ] `CrawlerEventListener` protocol in core
- [ ] `QtSignalAdapter` implements protocol
- [ ] Emits Qt signals for GUI updates
- [ ] Core has no Qt imports
- [ ] Unit tests

**Dependencies**: P7.1, P4.2

**Files**
- `src/ui/signal_adapter.py`
- `tests/ui/test_signal_adapter.py`

**Estimated Hours**: 2

---

## Phase 8: Testing & Polish

### P8.1 — Unit Tests for All Modules

**Description**  
Achieve ≥80% code coverage.

**Acceptance Criteria**
- [ ] All modules have corresponding test files
- [ ] `pytest --cov` shows ≥80%
- [ ] Edge cases covered
- [ ] Mocks used appropriately

**Dependencies**: All previous phases

**Files**
- `tests/**/*.py`

**Estimated Hours**: 8

---

### P8.2 — Integration Tests with Emulator

**Description**  
End-to-end crawl scenarios.

**Acceptance Criteria**
- [ ] Test fixture sets up Android emulator
- [ ] Sample app installed
- [ ] Full crawl runs without errors
- [ ] Statistics verified

**Dependencies**: All previous phases

**Files**
- `tests/integration/test_full_crawl.py`
- `tests/integration/conftest.py`

**Estimated Hours**: 4

---

### P8.3 — Error Handling Review

**Description**  
Verify all edge cases from spec are handled.

**Acceptance Criteria**
- [ ] Each edge case in spec has test
- [ ] Error messages are user-friendly
- [ ] No unhandled exceptions in logs
- [ ] Recovery behaviors verified

**Dependencies**: All previous phases

**Files**
- `tests/integration/test_error_handling.py`

**Estimated Hours**: 2

---

### P8.4 — Performance Profiling

**Description**  
Identify and address bottlenecks.

**Acceptance Criteria**
- [ ] Profile 100-step crawl
- [ ] Screenshot processing < 500ms
- [ ] DB operations < 50ms
- [ ] Memory stable over long runs

**Dependencies**: P4.2

**Files**
- `scripts/profile_crawl.py`

**Estimated Hours**: 2

---

### P8.5 — Documentation

**Description**  
README, CLI help, GUI tooltips.

**Acceptance Criteria**
- [ ] README with setup, usage, architecture
- [ ] CLI `--help` complete for all commands
- [ ] GUI tooltips on key elements
- [ ] Architecture diagram

**Dependencies**: All previous phases

**Files**
- `README.md`
- `docs/architecture.md`
- `docs/cli-user-guide.md`
- `docs/gui-user-guide.md`

**Estimated Hours**: 3

---

### P8.6 — Sample Apps for Testing

**Description**  
Create or curate test APKs.

**Acceptance Criteria**
- [ ] 2-3 sample APKs with known screen counts
- [ ] Include login flow, scrolling content, navigation
- [ ] Document expected behaviors

**Dependencies**: None

**Files**
- `test_apps/README.md`
- `test_apps/*.apk`

**Estimated Hours**: 2

---

## Summary

| Phase | Tasks | Total Hours |
|-------|-------|-------------|
| Phase 0 | 5 | 7.5 |
| Phase 1 | 7 | 12.5 |
| Phase 2 | 7 | 14.5 |
| Phase 3 | 7 | 17.5 |
| Phase 4 | 8 | 19 |
| Phase 5 | 4 | 12 |
| Phase 6 | 6 | 8 |
| Phase 7 | 10 | 23.5 |
| Phase 8 | 6 | 21 |
| **Total** | **60** | **135.5 hours** |

---

## Task Dependencies Graph

```
P0.1 ─┬─ P0.2
      ├─ P0.3
      ├─ P0.4 ─── P4.1
      ├─ P0.5
      ├─ P1.1 ─┬─ P1.4 ─── P4.2
      │        ├─ P1.5 ─┬─ P1.6 ─── P4.5
      │        │        └─ P4.3
      │        └─ P4.6
      ├─ P1.2 ─── P1.3
      ├─ P1.7
      ├─ P2.1 ─┬─ P2.2
      │        ├─ P2.3 ─── P4.4
      │        ├─ P2.4
      │        ├─ P2.5
      │        ├─ P2.6
      │        └─ P2.7
      ├─ P3.1 ─┬─ P3.2 ─┐
      │        ├─ P3.3 ─┼─ P3.5 ─── P3.6
      │        └─ P3.4 ─┘
      ├─ P3.7
      ├─ P6.1 ─┬─ P6.2
      │        ├─ P6.3
      │        ├─ P6.4
      │        ├─ P6.5
      │        └─ P6.6
      └─ P7.1 ─┬─ P7.2
               ├─ P7.3
               ├─ P7.4
               ├─ P7.5
               ├─ P7.6
               ├─ P7.7
               ├─ P7.8
               ├─ P7.9
               └─ P7.10
```

---

> **Next Step**: Begin with P0.1 (Initialize Python Project Structure)
