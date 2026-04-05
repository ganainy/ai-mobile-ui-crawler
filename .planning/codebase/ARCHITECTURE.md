# Architecture

**Analysis Date:** 2026-04-05

## Pattern Overview

**Overall:** Clean Domain-Driven Design with hexagonal architecture layers

**Key Characteristics:**
- Clear separation of concerns with CLI, Domain, Core, and Infrastructure layers
- DroidRun AI agent integration for intelligent mobile exploration
- Event-driven architecture with listener pattern for crawl lifecycle
- SQLite persistence with repository pattern for data access
- Command and Query separation for CLI operations

## Layers

**CLI Layer:**
- Purpose: Command-line interface entry point and command handling
- Location: `src/mobile_crawler/cli/`
- Contains: Click command definitions and command handlers
- Depends on: Domain layer for business logic
- Used by: End users via command line

**Domain Layer:**
- Purpose: Core business logic and domain models
- Location: `src/mobile_crawler/domain/`
- Contains: AI agents, action execution, screen tracking, and core models
- Depends on: Core layer for orchestration
- Used by: CLI and UI layers (if present)

**Core Layer:**
- Purpose: Application orchestration and coordination
- Location: `src/mobile_crawler/core/`
- Contains: Crawl controller, state machine, event system, and logging
- Depends on: Domain layer for business objects
- Used by: CLI layer to manage execution

**Infrastructure Layer:**
- Purpose: External systems and persistence abstraction
- Location: `src/mobile_crawler/infrastructure/`
- Contains: Database, ADB client, Appium driver, repositories
- Depends on: Config layer for settings
- Used by: Domain and Core layers

## Data Flow

**Crawl Execution Flow:**

1. CLI command triggers crawl via `crawl` command
2. CrawlController manages state transitions (RUNNING/PAUSED/STOPPED)
3. CrawlerLoop wraps DroidRun agent service
4. DroidRunAgentService executes AI-guided exploration
5. ActionExecutors perform actual device interactions
6. Events emitted to listeners throughout the process
7. Screen deduplication via perceptual hashing
8. Results persisted to SQLite via repositories

**Configuration Flow:**

1. ConfigManager loads defaults, user config, and environment
2. Settings cascaded through layers via dependency injection
3. Configuration used to initialize infrastructure components
4. Runtime updates reflected in service layer

## Key Abstractions

**CrawlController:**
- Purpose: Thread-safe crawl state management
- Examples: `src/mobile_crawler/core/crawl_controller.py`
- Pattern: State machine with observer pattern

**DroidRunAgentService:**
- Purpose: AI-driven mobile app exploration service
- Examples: `src/mobile_crawler/domain/droidrun_agent_service.py`
- Pattern: Adapter pattern for DroidRun integration

**RunRepository:**
- Purpose: Data access abstraction for crawl runs
- Examples: `src/mobile_crawler/infrastructure/run_repository.py`
- Pattern: Repository pattern with SQLite backend

**ActionExecutor:**
- Purpose: Platform-specific action execution abstraction
- Examples: `src/mobile_crawler/domain/action_executor.py`, `src/mobile_crawler/domain/adb_action_executor.py`
- Pattern: Strategy pattern for different execution backends

## Entry Points

**CLI Entry:**
- Location: `src/mobile_crawler/cli/main.py`
- Triggers: Command line invocations
- Responsibilities: Parse arguments and delegate to appropriate commands

**Crawl Execution:**
- Location: `src/mobile_crawler/cli/commands/crawl.py`
- Triggers: Crawl command execution
- Responsibilities: Initialize services and start crawl loop

**AI Interaction:**
- Location: `src/mobile_crawler/domain/droidrun_agent_service.py`
- Triggers: AI model calls for action recommendations
- Responsibilities: Format requests and process AI responses

## Error Handling

**Strategy:** Layered error handling with graceful degradation

**Patterns:**
- Recovery mechanisms for device disconnections
- Retry logic for AI model failures
- Event-based error notifications to listeners
- Persistent error state in database for failed runs

## Cross-Cutting Concerns

**Logging:** Structured logging with JSONL output per run
**Validation:** Pre-crawl validation of device and app state
**Authentication:** Configurable API keys for AI providers
**Monitoring:** Runtime statistics collection and reporting

---

*Architecture analysis: 2026-04-05*