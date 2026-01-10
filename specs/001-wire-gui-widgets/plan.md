# Implementation Plan: Wire Up GUI Widgets

**Branch**: `001-wire-gui-widgets` | **Date**: 2026-01-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-wire-gui-widgets/spec.md`

## Summary

Connect all existing UI widgets (DeviceSelector, AppSelector, AIModelSelector, CrawlControlPanel, LogViewer, StatsDashboard, SettingsPanel, RunHistoryView) to the MainWindow in a coherent layout. Wire widget signals to backend services (DeviceDetection, ProviderRegistry, CrawlerLoop) using QtSignalAdapter for thread-safe event bridging. Enable complete AI-powered crawl execution from the GUI.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: PySide6 6.x, existing mobile_crawler modules  
**Storage**: SQLite via existing DatabaseManager  
**Testing**: pytest with pytest-qt for GUI testing  
**Target Platform**: Windows/Linux desktop  
**Project Type**: Single Python project with GUI  
**Performance Goals**: UI remains responsive during crawl; log updates < 500ms  
**Constraints**: Background threading for crawl operations; no UI freezing  
**Scale/Scope**: Single-user desktop application

## Constitution Check

*GATE: Constitution is a placeholder template - no specific constraints to check.*

✓ No constitution violations detected (template not customized)

## Project Structure

### Documentation (this feature)

```text
specs/001-wire-gui-widgets/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (existing structure)

```text
src/mobile_crawler/
├── ui/
│   ├── main_window.py       # MODIFY: Add widget layout and wiring
│   ├── signal_adapter.py    # EXISTS: Qt signal bridge
│   ├── widgets/
│   │   ├── ai_model_selector.py    # EXISTS
│   │   ├── app_selector.py         # EXISTS
│   │   ├── crawl_control_panel.py  # EXISTS
│   │   ├── device_selector.py      # EXISTS
│   │   ├── log_viewer.py           # EXISTS
│   │   ├── run_history_view.py     # EXISTS
│   │   ├── settings_panel.py       # EXISTS
│   │   └── stats_dashboard.py      # EXISTS
├── core/
│   ├── crawler_loop.py             # EXISTS: CrawlerLoop
│   ├── crawl_state_machine.py      # EXISTS: CrawlState
│   └── crawl_controller.py         # EXISTS: CrawlController
├── infrastructure/
│   ├── device_detection.py         # EXISTS: DeviceDetection
│   ├── appium_driver.py            # EXISTS: AppiumDriver
│   └── user_config_store.py        # EXISTS: UserConfigStore
└── domain/
    └── providers/
        ├── registry.py             # EXISTS: ProviderRegistry
        └── vision_detector.py      # EXISTS: VisionDetector

tests/
├── ui/
│   ├── test_main_window.py         # CREATE: Integration tests
│   └── test_widget_wiring.py       # CREATE: Signal connection tests
```

**Structure Decision**: Use existing project structure. MainWindow is the only file requiring significant modification. Widget classes exist but need instantiation and signal connections in MainWindow.

## Complexity Tracking

No constitution violations - no complexity justification needed.

---

## Phase 0: Research

All technologies and patterns are already established in the codebase:

### Decision 1: Widget Layout Approach
- **Decision**: Use QSplitter with QVBoxLayout/QHBoxLayout for flexible layout
- **Rationale**: Standard PySide6 pattern already used in widget files
- **Alternatives**: QDockWidget (too complex), fixed positions (not responsive)

### Decision 2: Thread-Safe Event Handling
- **Decision**: Use existing QtSignalAdapter as CrawlerEventListener
- **Rationale**: Already implemented and follows proper Qt threading model
- **Alternatives**: Direct method calls (would cause thread violations)

### Decision 3: Service Instantiation
- **Decision**: Create services in MainWindow.__init__, pass to widgets via constructor
- **Rationale**: Dependency injection pattern already used in widgets
- **Alternatives**: Global singletons (harder to test), factory pattern (overkill)

### Decision 4: Configuration Persistence
- **Decision**: Use existing UserConfigStore for API keys and preferences
- **Rationale**: Already implemented with proper encryption for sensitive data
- **Alternatives**: QSettings (doesn't support encryption), plain files (insecure)

---

## Phase 1: Design

### Data Model

No new entities needed. Using existing:
- `CrawlState` enum from `crawl_state_machine.py`
- `AndroidDevice` from `device_detection.py`
- `Run`, `StepLog` from `domain/models.py`

### Contracts

No new APIs. Internal widget signal/slot connections:

| Widget | Signal | Handler |
|--------|--------|---------|
| DeviceSelector | device_selected(AndroidDevice) | MainWindow._on_device_selected |
| AppSelector | app_selected(str) | MainWindow._on_app_selected |
| AIModelSelector | model_selected(str, str) | MainWindow._on_model_selected |
| CrawlControlPanel | start_requested() | MainWindow._start_crawl |
| CrawlControlPanel | pause_requested() | MainWindow._pause_crawl |
| CrawlControlPanel | resume_requested() | MainWindow._resume_crawl |
| CrawlControlPanel | stop_requested() | MainWindow._stop_crawl |
| QtSignalAdapter | step_completed(...) | StatsDashboard.update_stats |
| QtSignalAdapter | crawl_completed(...) | MainWindow._on_crawl_completed |

### Quickstart

To run the GUI after implementation:

```bash
# From project root
pip install -e .
mobile-crawler-gui

# Or directly
python -m mobile_crawler.ui.main_window
```

Prerequisites:
1. Android device connected via ADB
2. Appium server running: `npx appium -p 4723 --relaxed-security`
3. AI provider API key configured in Settings panel

---

## Implementation Tasks

### Task 1: Update MainWindow Layout (P1)
**File**: `src/mobile_crawler/ui/main_window.py`

Add widget instantiation and layout:
- Create services (DeviceDetection, ProviderRegistry, etc.)
- Instantiate all widgets with proper dependencies
- Arrange in QSplitter layout:
  - Left panel: DeviceSelector, AppSelector, AIModelSelector, SettingsPanel
  - Center: CrawlControlPanel, StatsDashboard
  - Right: LogViewer
  - Bottom: RunHistoryView

**Acceptance**: All widgets visible in main window

### Task 2: Wire Device and App Selection (P1)
**File**: `src/mobile_crawler/ui/main_window.py`

Connect signals:
- DeviceSelector.device_selected → update AppSelector device
- AppSelector.app_selected → store selected package
- Enable Start button when device + app + AI configured

**Acceptance**: Can select device, see apps, select target app

### Task 3: Wire AI Model Selection (P1)
**File**: `src/mobile_crawler/ui/main_window.py`

Connect signals:
- AIModelSelector.model_selected → store provider/model config
- SettingsPanel API key changes → validate and store
- Update Start button enabled state

**Acceptance**: Can select provider, enter API key, see models

### Task 4: Wire Crawl Controls (P1)
**File**: `src/mobile_crawler/ui/main_window.py`

Connect signals:
- CrawlControlPanel.start_requested → create CrawlerLoop, start crawl
- pause/resume/stop → call CrawlerLoop methods
- Run crawl in QThread to keep UI responsive

**Acceptance**: Start/Pause/Resume/Stop buttons work correctly

### Task 5: Wire Log Viewer (P1)
**File**: `src/mobile_crawler/ui/main_window.py`

Connect QtSignalAdapter signals to LogViewer:
- step_started → log step info
- action_executed → log action result
- error_occurred → log error

**Acceptance**: Logs appear in real-time during crawl

### Task 6: Wire Stats Dashboard (P1)
**File**: `src/mobile_crawler/ui/main_window.py`

Connect QtSignalAdapter signals to StatsDashboard:
- step_completed → update step count
- crawl_completed → show final stats
- Elapsed time updates via QTimer

**Acceptance**: Stats update during crawl

### Task 7: Wire Run History (P3)
**File**: `src/mobile_crawler/ui/main_window.py`

Connect RunHistoryView:
- Load history from RunRepository on startup
- Refresh after crawl completes

**Acceptance**: Can view past runs

### Task 8: Add GUI Tests (P2)
**File**: `tests/ui/test_main_window.py`

Create pytest-qt tests:
- Test window launches with all widgets
- Test signal connections work
- Test button state changes

**Acceptance**: pytest passes for UI tests
