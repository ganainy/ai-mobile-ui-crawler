# Implementation Plan: AI-Powered Android Exploration Tool

> **Based on**: `speckit.product-spec.md`  
> **Created**: 2026-01-10

---

## Overview

This plan breaks down the product specification into implementable phases, ordered by dependency and priority. Each phase produces a working increment.

---

## Phase 0: Project Foundation

**Goal**: Establish project structure, tooling, and shared infrastructure.

### Tasks

| ID | Task | Output | Estimated Effort |
|----|------|--------|------------------|
| 0.1 | Initialize Python project with `pyproject.toml` | Package config, dependencies | 1h |
| 0.2 | Set up directory structure | `core/`, `infrastructure/`, `domain/`, `ui/`, `cli/`, `config/`, `utils/` | 30m |
| 0.3 | Configure linting (Ruff) and formatting (Black) | `.ruff.toml`, `pyproject.toml` | 30m |
| 0.4 | Set up pytest with fixtures | `pytest.ini`, `tests/` structure | 1h |
| 0.5 | Create logging infrastructure | `LoggingService` with multi-sink architecture | 2h |
| 0.6 | Implement configuration system | Config precedence (SQLite → env → defaults) | 2h |

### Deliverables
- [ ] Runnable project skeleton
- [ ] `python -m pytest` passes with placeholder test
- [ ] Logging works to console/file

---

## Phase 1: Database & Storage Layer

**Goal**: Implement persistence layer for crawl data and user config.

### Tasks

| ID | Task | Output | Estimated Effort |
|----|------|--------|------------------|
| 1.1 | Create `crawler.db` schema | `runs`, `screens`, `step_logs`, `transitions`, `run_stats`, `ai_interactions` tables | 2h |
| 1.2 | Create `user_config.db` schema | `user_config`, `secrets` tables | 1h |
| 1.3 | Implement database manager | Connection pooling, migrations, WAL mode | 2h |
| 1.4 | Implement secrets encryption | Fernet encryption with machine-bound key | 2h |
| 1.5 | Implement run CRUD operations | Create, read, update, delete runs with cascade | 2h |
| 1.6 | Implement screen state storage | Screen hashing, deduplication, visit tracking | 2h |
| 1.7 | Implement session folder management | Create/delete `output_data/{session}/` folders | 1h |

### Deliverables
- [ ] Both databases created with full schema
- [ ] Unit tests for CRUD operations
- [ ] Secrets stored encrypted

---

## Phase 2: Appium Integration

**Goal**: Establish device control via Appium.

### Tasks

| ID | Task | Output | Estimated Effort |
|----|------|--------|------------------|
| 2.1 | Implement Appium driver wrapper | `AppiumDriver` class with session management | 3h |
| 2.2 | Implement device detection | List connected devices via ADB | 1h |
| 2.3 | Implement screenshot capture | Capture + downscale to max 1280px | 1h |
| 2.4 | Implement action executor | `click`, `input`, `long_press`, `scroll_*`, `swipe_*`, `back` | 4h |
| 2.5 | Implement gesture handler | Coordinate calculation from bounding box | 1h |
| 2.6 | Implement video recording manager | Start/stop via Appium API, save to file | 2h |
| 2.7 | Implement app context manager | Package detection, context loss handling | 2h |

### Deliverables
- [ ] Can connect to device, launch app, execute all 8 action types
- [ ] Video recording works
- [ ] Integration tests with emulator

---

## Phase 3: AI Provider Integration

**Goal**: Implement pluggable AI providers with vision support.

### Tasks

| ID | Task | Output | Estimated Effort |
|----|------|--------|------------------|
| 3.1 | Define `ModelAdapter` abstract interface | ABC with `initialize`, `generate_response`, `model_info` | 1h |
| 3.2 | Implement `GeminiAdapter` | Google Gemini integration | 3h |
| 3.3 | Implement `OpenRouterAdapter` | OpenRouter API integration | 3h |
| 3.4 | Implement `OllamaAdapter` | Local Ollama integration | 3h |
| 3.5 | Implement vision detection | Filter models by vision capability | 2h |
| 3.6 | Implement AI interaction service | Request building, response parsing, retry logic | 3h |
| 3.7 | Implement prompt builder | System prompt + exploration journal formatting | 2h |

### Deliverables
- [ ] All 3 providers working
- [ ] Vision-only model filtering
- [ ] Response schema validation

---

## Phase 4: Crawler Core

**Goal**: Implement the main crawl loop and state machine.

### Tasks

| ID | Task | Output | Estimated Effort |
|----|------|--------|------------------|
| 4.1 | Implement crawl state machine | States: `UNINITIALIZED` → `RUNNING` → `STOPPED` etc. | 2h |
| 4.2 | Implement crawler loop | Main iteration: screenshot → AI → execute → log | 4h |
| 4.3 | Implement stuck detector | Consecutive visit tracking, `is_stuck` flag | 2h |
| 4.4 | Implement screen state manager | Visual hashing, similarity detection (threshold=5) | 3h |
| 4.5 | Implement exploration journal | Query last 15 steps from `step_logs` | 1h |
| 4.6 | Implement runtime statistics collector | Track all 60+ metrics | 3h |
| 4.7 | Implement pause/resume/stop controls | Thread-safe flag management | 2h |
| 4.8 | Implement pre-crawl validation | All required checks before start | 2h |

### Deliverables
- [ ] Full crawl loop working end-to-end
- [ ] Pause/resume/stop functional
- [ ] Statistics collected and persisted

---

## Phase 5: External Integrations

**Goal**: Integrate PCAPdroid, MobSF, and reporting.

### Tasks

| ID | Task | Output | Estimated Effort |
|----|------|--------|------------------|
| 5.1 | Implement PCAPdroid manager | Start/stop via intent API, pull PCAP file | 3h |
| 5.2 | Implement MobSF manager | APK extraction, upload, results retrieval | 3h |
| 5.3 | Implement PDF report generator | ReportLab-based summary report | 4h |
| 5.4 | Implement stale run cleanup | Recover partial artifacts on startup | 2h |

### Deliverables
- [ ] Traffic capture working
- [ ] Static analysis results saved
- [ ] PDF reports generated

---

## Phase 6: CLI Interface

**Goal**: Implement command-line interface.

### Tasks

| ID | Task | Output | Estimated Effort |
|----|------|--------|------------------|
| 6.1 | Set up Click framework | Entry point `run_cli.py` | 1h |
| 6.2 | Implement `crawl` command | Start crawl with options | 2h |
| 6.3 | Implement `config` commands | Set/get API keys, preferences | 2h |
| 6.4 | Implement `report` command | Generate report for past run | 1h |
| 6.5 | Implement `list` commands | List runs, devices | 1h |
| 6.6 | Implement JSON event output | Structured events to stdout | 2h |

### Deliverables
- [ ] Full CLI functional
- [ ] JSON output pipeable
- [ ] Help text for all commands

---

## Phase 7: GUI Interface

**Goal**: Implement graphical user interface.

### Tasks

| ID | Task | Output | Estimated Effort |
|----|------|--------|------------------|
| 7.1 | Set up PySide6 application | Entry point `run_ui.py`, main window | 2h |
| 7.2 | Implement device selection widget | Dropdown with detected devices | 2h |
| 7.3 | Implement app selection widget | Package input + validation | 1h |
| 7.4 | Implement AI provider/model selection | Provider dropdown, model list with vision filter | 3h |
| 7.5 | Implement crawl control panel | Start/Pause/Resume/Stop buttons | 2h |
| 7.6 | Implement real-time log viewer | Scrolling log with level filtering | 2h |
| 7.7 | Implement statistics dashboard | Live metrics display | 3h |
| 7.8 | Implement settings panel | API keys, system prompt, crawl limits | 3h |
| 7.9 | Implement run history view | List past runs, delete, generate report | 3h |
| 7.10 | Implement Qt signal adapter | Bridge core events to GUI without Qt in core | 2h |

### Deliverables
- [ ] Full GUI functional
- [ ] Real-time updates during crawl
- [ ] Settings persist across sessions

---

## Phase 8: Testing & Polish

**Goal**: Comprehensive testing and documentation.

### Tasks

| ID | Task | Output | Estimated Effort |
|----|------|--------|------------------|
| 8.1 | Unit tests for all modules | ≥80% coverage | 8h |
| 8.2 | Integration tests with emulator | End-to-end crawl scenarios | 4h |
| 8.3 | Error handling review | Verify all edge cases handled | 2h |
| 8.4 | Performance profiling | Identify bottlenecks | 2h |
| 8.5 | Documentation | README, CLI help, GUI tooltips | 3h |
| 8.6 | Sample apps for testing | 2-3 test APKs with known screens | 2h |

### Deliverables
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Ready for release

---

## Dependency Graph

```
Phase 0 (Foundation)
    │
    ├── Phase 1 (Database)
    │       │
    │       ├── Phase 2 (Appium) ──────┐
    │       │                          │
    │       └── Phase 3 (AI Providers) │
    │               │                  │
    │               └──────────────────┼── Phase 4 (Crawler Core)
    │                                  │         │
    │                                  │         ├── Phase 5 (Integrations)
    │                                  │         │
    │                                  │         ├── Phase 6 (CLI)
    │                                  │         │
    │                                  │         └── Phase 7 (GUI)
    │                                  │                 │
    └──────────────────────────────────┴─────────────────┴── Phase 8 (Testing)
```

---

## Estimated Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 0: Foundation | 1 day | 1 day |
| Phase 1: Database | 1.5 days | 2.5 days |
| Phase 2: Appium | 2 days | 4.5 days |
| Phase 3: AI Providers | 2 days | 6.5 days |
| Phase 4: Crawler Core | 2.5 days | 9 days |
| Phase 5: Integrations | 1.5 days | 10.5 days |
| Phase 6: CLI | 1 day | 11.5 days |
| Phase 7: GUI | 3 days | 14.5 days |
| Phase 8: Testing | 2.5 days | **17 days** |

**Total estimated effort**: ~17 working days (3-4 weeks)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| AI response schema violations | Strict validation + fallback to single-action mode |
| Appium session instability | Automatic reconnection with exponential backoff |
| Large screenshot memory usage | Downscale before AI call; stream to disk |
| PCAPdroid not responding | Graceful degradation; crawl continues without capture |
| Vision model filtering inaccurate | Cache model metadata; manual override option |

---

## Success Metrics (Post-Implementation)

1. **Coverage**: ≥80% of reachable screens explored in sample apps
2. **Stability**: Zero crashes in 100-step crawls across 5 apps
3. **Latency**: <5s/step (Ollama), <8s/step (cloud)
4. **Test Coverage**: ≥80% code coverage
5. **User Satisfaction**: CLI and GUI both fully functional

---

## Next Steps

1. ✅ Create this implementation plan
2. ⬜ Begin Phase 0: Project Foundation
3. ⬜ Set up CI with GitHub Actions (optional)

---

> **Note**: Phases can be parallelized where dependencies allow. Phase 6 (CLI) and Phase 7 (GUI) can be developed in parallel after Phase 4.
