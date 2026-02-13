# Research: UI/UX Improvements

**Feature**: UI/UX Improvements (Branch: `020-ui-ux-improvements`)
**Date**: 2025-01-15

## 1. Threading Strategy for Long-Running Operations

**Problem**: `DeviceSelector`, `AppSelector`, and `AIModelSelector` perform blocking I/O operations (ADB commands, network requests) on the main UI thread, causing freezes.

**Decision**: Use `QThread` with the Worker-Object pattern.

**Rationale**:
- **Responsiveness**: Moves heavy lifting off the main event loop.
- **PySide6 Best Practice**: Subclassing `QThread` is often discouraged in favor of a Worker `QObject` moved to a `QThread`, but for simple "run and done" tasks, a unified `WorkerThread` or specialized `QThread` subclass is acceptable and robust. Given `CrawlerWorker` already inherits `QThread`, we will follow the existing pattern or use a lightweight `QRunnable` + `QThreadPool` if the operations are frequent and short.
- **Decision**: We will implement a reusable `AsyncOperation(QThread)` class that takes a callable target to minimize boilerplate for `refresh_devices`, `list_apps`, etc.

**Alternatives Considered**:
- `QRunnable` + `QThreadPool`: Good for fire-and-forget, but handling signals (results/errors) back to UI thread requires a separate `QObject` signal emitter anyway. `QThread` is simpler for this localized usage.
- `asyncio` with `qasync`: Too complex to introduce an entire async loop integration if not already present.

## 2. UI Organization: Settings Panel

**Problem**: `SettingsPanel` is a long vertical list requiring scrolling.

**Decision**: Refactor `SettingsPanel` to use `QTabWidget`.

**Proposed Tabs**:
1.  **General**: Crawl Limits, Screen Configuration.
2.  **AI**: API Keys (Gemini, OpenRouter), System Prompt.
3.  **Integrations**: Traffic Capture (PCAPdroid), MobSF Analysis, Video Recording.
4.  **Credentials**: Test Credentials, Mailosaur Config.

**Rationale**:
- **Categorization**: Groups related settings logically.
- **Space Efficiency**: Eliminates the need for a giant scrollable area (though individual tabs can still scroll if needed).

## 3. UI Organization: Menus

**Problem**: File and Help menus are largely placeholders (`Exit` and `About` only).

**Decision**:
- **File Menu**: Keep. Add "Open Logs Folder" or "Open Session Folder". "Exit" is standard.
- **Help Menu**: Keep. Add "Documentation" (link), "Report Issue" (link).
- **Cleanup**: Remove any separators or items that don't do anything.

**Rationale**: standard desktop apps usually have these. Removing them entirely feels "non-standard". Populating them with *useful* actions (like opening the session folder which was a previous user pain point) is better UX.

## 4. Space Optimization (Center Panel)

**Problem**: Gaps between "Crawl Controls" and "Statistics".

**Decision**:
- Adjust `QVBoxLayout` stretch factors.
- Review `CrawlControlPanel` and `StatsDashboard` for internal `addStretch()` calls that might be excessive.
- Ensure `StatsDashboard` expands to fill available vertical space rather than being pushed down.

## 5. Persistence for Step-by-Step Mode

**Problem**: Setting is lost on restart.

**Decision**: Add `step_by_step_enabled` key to `UserConfigStore`.

**Implementation**:
- Load in `CrawlControlPanel.__init__` (or pass from Main Window).
- Save on toggle signal.

## 6. Run History Visibility

**Problem**: Table is too short.

**Decision**:
- Set a generic `minimumHeight` for the `RunHistoryView`.
- In `MainWindow`, the `QSplitter` or layout managing the bottom panel needs to prioritize giving it some height or set a balanced initial size.

## Action Plan Impacts

- **New Classes**: `AsyncOperation` (generic worker thread).
- **Refactors**:
    - `SettingsPanel`: Split big layout into Tabs.
    - `DeviceSelector`, `AppSelector`, `AIModelSelector`: Wrap IO calls in `AsyncOperation`.
    - `MainWindow`: Persistence wiring, layout tuning.
