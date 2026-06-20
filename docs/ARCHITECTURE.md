<!-- refreshed: 2026-06-04 -->
# Architecture

**Analysis Date:** 2026-06-04

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                 Interface / Entry Layer                      │
├──────────────────┬──────────────────┬───────────────────────┤
│   CLI            │   GUI            │   Startup scripts      │
│  `run_cli.py`    │ `run_ui.py`      │ `scripts/start.ps1`    │
│  `src/mobile_`   │ `src/mobile_`    │                        │
│  `crawler/cli/*` │ `crawler/ui/*`   │                        │
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 Orchestration / Domain                       │
│  `src/mobile_crawler/core/*` + `src/mobile_crawler/domain/*`│
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│          Persistence / Artifacts / Internal Agent Runtime     │
│ `src/mobile_crawler/infrastructure/*` + `domain/crawler_agent`│
│ SQLite (`crawler.db`, `user_config.db`) + session folders   │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI command surface | Parses commands/options and starts crawl/config/report/list/delete workflows | `src/mobile_crawler/cli/main.py`, `src/mobile_crawler/cli/commands/*.py` |
| GUI shell | Builds widgets, wires Qt signals, starts crawl worker thread, updates dashboards | `src/mobile_crawler/ui/main_window.py`, `src/mobile_crawler/ui/signal_adapter.py` |
| Crawl orchestrator | Owns crawl lifecycle, emits events, delegates exploration to the internalized agent service | `src/mobile_crawler/core/crawler_loop.py` |
| Domain integration services | Adapts provider/model discovery, internalized crawler agent behavior, parser settings, and reporting orchestration | `src/mobile_crawler/domain/crawler_agent_service.py`, `src/mobile_crawler/domain/crawler_agent/`, `src/mobile_crawler/domain/providers/*.py`, `src/mobile_crawler/domain/report_generator.py` |
| Infrastructure repositories | Handles SQLite schema/migrations and data CRUD for runs/screens/steps/AI interactions | `src/mobile_crawler/infrastructure/database.py`, `src/mobile_crawler/infrastructure/*_repository.py` |
| Artifact/session layout | Creates and resolves run folder topology (screenshots, reports, pcap, logs, data) | `src/mobile_crawler/infrastructure/session_folder_manager.py` |

## Pattern Overview

**Overall:** Layered modular monolith with repository pattern + event-listener bridge + internalized agent runtime

**Key Characteristics:**
- Interface layers (`cli`, `ui`) call into `core` orchestration and avoid direct SQL.
- `core` emits listener events via `CrawlerEventListener` contract (`src/mobile_crawler/core/crawler_event_listener.py`).
- `infrastructure` encapsulates external system calls (ADB, SQLite, MobSF, file system).
- `domain/crawler_agent` contains the active agent runtime that was formerly external.

## Layers

**Interface Layer:**
- Purpose: Accept user intent and map it to crawl/report/config operations.
- Location: `run_cli.py`, `run_ui.py`, `src/mobile_crawler/cli/`, `src/mobile_crawler/ui/`
- Contains: Click commands, Qt widgets, startup helpers.
- Depends on: `config`, `core`, `domain`, `infrastructure`.
- Used by: End users and scripts.

**Application/Core Layer:**
- Purpose: Crawl lifecycle orchestration, state transitions, event emission.
- Location: `src/mobile_crawler/core/`
- Contains: `CrawlerLoop`, control/state helpers, logging bridges.
- Depends on: `domain` services + `infrastructure` repositories/managers.
- Used by: CLI command `crawl` and GUI `MainWindow`.

**Domain Services Layer:**
- Purpose: Provider/model logic, internalized crawler-agent adapter logic, reporting assembly, parser configuration, and grounding.
- Location: `src/mobile_crawler/domain/`
- Contains: `CrawlerAgentService`, internalized `crawler_agent`, provider registry, models, report generator, OCR grounding modules.
- Depends on: `config`, `infrastructure`, external SDKs.
- Used by: `core` and UI service creation.

**Infrastructure Layer:**
- Purpose: Persistence, filesystem artifacts, ADB/process integration, feature managers.
- Location: `src/mobile_crawler/infrastructure/`
- Contains: DB manager, repositories, session folders, device detection, MobSF and export utilities.
- Depends on: SQLite, OS, subprocess tools, HTTP clients.
- Used by: all upper layers.

## Data Flow

### Primary Request Path

1. CLI or GUI starts crawl (`src/mobile_crawler/cli/commands/crawl.py:180`, `src/mobile_crawler/ui/main_window.py:348`).
2. Run row is created and crawler loop invoked (`src/mobile_crawler/cli/commands/crawl.py:228`, `src/mobile_crawler/core/crawler_loop.py:125`).
3. `CrawlerLoop` creates session folder + updates run path (`src/mobile_crawler/core/crawler_loop.py:141`, `src/mobile_crawler/infrastructure/session_folder_manager.py:31`).
4. `CrawlerLoop` delegates exploration to `CrawlerAgentService`, which wraps the internalized `crawler_agent` runtime.
5. Final status/stats are persisted, then completion event is emitted (`src/mobile_crawler/core/crawler_loop.py:232`, `src/mobile_crawler/core/crawler_loop.py:246`).

### Step Timing Diagnostics

1. The internal `crawler_agent` workflows emit app-card, Manager LLM, Manager validation retry, Executor LLM, and tool execution timing fields on their existing workflow events.
2. `CrawlerAgentService` buffers those workflow timings until each `ToolExecutionEvent` establishes the crawl step number, then writes sub-phase timing metadata into `step_phase_transitions.metadata_json` on the matching DECIDE, EXECUTE, or RECORD transition.
3. The GUI mounts `AIMonitorPanel` beside the log viewer and uses `StepPhaseRepository.get_transitions_for_step()` to render per-step timing breakdowns and Manager validation retry reasons in the AI Monitor detail view.

### Secondary Flow: Report Generation

1. UI/CLI requests report (`src/mobile_crawler/ui/widgets/run_history_view.py`, `src/mobile_crawler/cli/commands/report.py:10`).
2. Domain report generator fetches run, steps, AI interactions (`src/mobile_crawler/domain/report_generator.py:53`, `src/mobile_crawler/domain/report_generator.py:57`, `src/mobile_crawler/domain/report_generator.py:74`).
3. Reporting correlator + Jinja generator create HTML output in run reports folder (`src/mobile_crawler/domain/report_generator.py:105`, `src/mobile_crawler/domain/report_generator.py:123`).

**State Management:**
- Persistent run/config state is SQLite-backed (`src/mobile_crawler/infrastructure/database.py`, `src/mobile_crawler/infrastructure/user_config_store.py`).
- In-memory runtime state lives in `MainWindow` fields and `CrawlerLoop` instance fields (`src/mobile_crawler/ui/main_window.py`, `src/mobile_crawler/core/crawler_loop.py`).

## Key Abstractions

**Event Listener Contract:**
- Purpose: Decouple crawler execution from UI/CLI outputs.
- Examples: `src/mobile_crawler/core/crawler_event_listener.py`, `src/mobile_crawler/ui/signal_adapter.py`, `src/mobile_crawler/cli/commands/crawl.py` (`JSONEventListener`)
- Pattern: Observer/listener.

**Repository Abstraction:**
- Purpose: Encapsulate SQL and row-to-dataclass mapping.
- Examples: `src/mobile_crawler/infrastructure/run_repository.py`, `src/mobile_crawler/infrastructure/step_log_repository.py`, `src/mobile_crawler/infrastructure/ai_interaction_repository.py`
- Pattern: Repository + dataclass DTOs.

**Session Artifact Manager:**
- Purpose: Standardize run output folders and path resolution.
- Examples: `src/mobile_crawler/infrastructure/session_folder_manager.py`
- Pattern: Centralized filesystem policy object.

## Entry Points

**CLI Entrypoint:**
- Location: `run_cli.py`, `src/mobile_crawler/cli/main.py`
- Triggers: `mobile-crawler-cli` script or direct Python execution.
- Responsibilities: Register Click command group and dispatch subcommands.

**GUI Entrypoint:**
- Location: `run_ui.py`, `src/mobile_crawler/ui/main_window.py:1515`
- Triggers: `mobile-crawler-gui` script or direct Python execution.
- Responsibilities: Build `QApplication`, instantiate `MainWindow`, start event loop.

**Startup Orchestration Script:**
- Location: `scripts/start.ps1`
- Triggers: Manual shell execution.
- Responsibilities: Optionally start MobSF and then launch the UI.

## Architectural Constraints

- **Threading:** Qt main thread + `QThread` worker (`src/mobile_crawler/ui/main_window.py:133`) plus dedicated crawl thread option in `CrawlerLoop.start` (`src/mobile_crawler/core/crawler_loop.py:58`) and per-run asyncio loop (`src/mobile_crawler/core/crawler_loop.py:263`).
- **Global state:** Module-level config singleton (`src/mobile_crawler/config/config_manager.py:103`) and root logger filters installed on import (`src/mobile_crawler/domain/crawler_agent_service.py:45`).
- **Circular imports:** Not detected in inspected modules; local imports are used in some UI helpers to avoid cycles (`src/mobile_crawler/ui/main_window.py:551`).
- **Internalized runtime:** Exploration logic is delegated to `src/mobile_crawler/domain/crawler_agent`; `CrawlerLoop` remains intentionally thin and manages run/session lifecycle around that runtime.

## Current Runtime State

- `src/mobile_crawler/domain/crawler_agent` is the active runtime namespace for `CrawlerAgent`, `CrawlerConfig`, drivers, UI state providers, OmniParser integration, macro replay, and telemetry support.
- `src/mobile_crawler/domain/crawler_agent_service.py` exposes `CrawlerAgentService`, the Mobile Crawler adapter around that internal runtime.
- UI settings are organized around General, AI Crawler, API Keys, and Integrations tabs.
- App test credentials include address, email, and phone fields that are matched contextually via `ContextAwareInputDictionary` to supply realistic inputs to the prompt builder.
- FSM state tracking via `StateGraphTracker` records structural layout XML hashes (excluding dynamic clock/battery elements) to build a state transition graph, detect loops, and supply recovery hints.
- Parser settings support `boost`, `omniparser`, and `accessibility` modes, with OmniParser backend selection between Replicate and a local FastAPI server.
- Completed planning docs are intentionally removed; durable architecture state lives in this file.

## Anti-Patterns

### Drifted Interface Usage

**What happens:** Some call sites reference methods that are not present in current classes (e.g., `src/mobile_crawler/cli/commands/delete.py` calls `get_session_folder`, and `src/mobile_crawler/cli/commands/list.py` calls `get_recent_runs`).  
**Why it's wrong:** It creates runtime failure risk and indicates stale coupling across layers.  
**Do this instead:** Use currently implemented APIs in `src/mobile_crawler/infrastructure/session_folder_manager.py` (`create_session_folder`, `get_session_path`) and `src/mobile_crawler/infrastructure/run_repository.py` (`get_all_runs`/explicit query methods) consistently across CLI/UI files.

## Error Handling

**Strategy:** Catch-and-emit around orchestration boundaries; keep crawl loop alive where possible.

**Patterns:**
- CLI commands wrap top-level actions with `try/except` and abort with Click errors (`src/mobile_crawler/cli/commands/*.py`).
- `CrawlerLoop.run` captures exceptions, emits `on_error`, and transitions to STOPPED in `finally` (`src/mobile_crawler/core/crawler_loop.py:254`).

## Cross-Cutting Concerns

**Logging:** Python logging + UI bridge handler + stdout/stderr capture (`src/mobile_crawler/core/log_sinks.py`, `src/mobile_crawler/ui/main_window.py`).  
**Validation:** UI pre-flight checks for selected device/package/model and required keys (`src/mobile_crawler/ui/main_window.py:404`).  
**Authentication:** API keys are read from encrypted config store and env fallbacks (`src/mobile_crawler/infrastructure/user_config_store.py`, `src/mobile_crawler/domain/crawler_agent_service.py:165`).

---

*Architecture analysis: 2026-06-04*
