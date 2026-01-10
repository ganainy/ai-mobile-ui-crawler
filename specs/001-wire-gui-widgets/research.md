# Research: Wire Up GUI Widgets

**Feature**: 001-wire-gui-widgets  
**Date**: 2026-01-10

## Research Tasks

### 1. Widget Layout Pattern in PySide6

**Task**: Find best practices for multi-panel desktop layouts

**Decision**: Use QSplitter with nested layouts
- **Rationale**: 
  - Allows user-resizable panels
  - Works well with existing QVBoxLayout-based widgets
  - Standard pattern in Qt applications
- **Alternatives Considered**:
  - QDockWidget: Adds floating/docking complexity not needed
  - QStackedWidget: Good for wizard/tabs, not multi-panel
  - Fixed layouts: Not responsive to window resize

**Source**: PySide6 documentation, existing mobile_crawler widget code

---

### 2. Thread-Safe GUI Updates

**Task**: Research Qt threading best practices for background operations

**Decision**: Use QtSignalAdapter (already implemented) with QThread for crawl
- **Rationale**:
  - QtSignalAdapter already bridges CrawlerEventListener to Qt signals
  - Qt signals are thread-safe across thread boundaries
  - QThread is standard Qt threading approach
- **Alternatives Considered**:
  - QRunnable/QThreadPool: Good for short tasks, not long-running crawls
  - Python threading.Thread: Works but QThread integrates better with Qt
  - asyncio: Would require significant architecture changes

**Source**: Qt documentation, existing signal_adapter.py implementation

---

### 3. Widget Dependencies

**Task**: Identify service dependencies for each widget

**Findings**:

| Widget | Dependencies |
|--------|-------------|
| DeviceSelector | DeviceDetection |
| AppSelector | AppiumDriver (for package list) |
| AIModelSelector | ProviderRegistry, VisionDetector |
| CrawlControlPanel | CrawlController |
| LogViewer | None (receives events) |
| StatsDashboard | None (receives events) |
| SettingsPanel | UserConfigStore |
| RunHistoryView | RunRepository |

**Decision**: Create services in MainWindow, inject into widgets
- **Rationale**: Dependency injection allows testing with mocks
- **Alternatives**: Singletons (harder to test), lazy creation (complex lifecycle)

---

### 4. Configuration Storage

**Task**: Research secure API key storage

**Decision**: Use existing UserConfigStore
- **Rationale**:
  - Already implemented with encryption for sensitive data
  - Supports typed get/set operations
  - File-based persistence already working
- **Alternatives Considered**:
  - QSettings: No encryption support
  - System keychain: Platform-specific complexity
  - Environment variables: Poor UX for GUI app

**Source**: Existing user_config_store.py implementation

---

### 5. AppSelector Package List

**Task**: Research how to get installed packages from device

**Decision**: Use ADB command via subprocess
- **Rationale**:
  - `adb shell pm list packages` is reliable
  - Already have device_id from DeviceSelector
  - No Appium session required
- **Alternative**: Appium driver.get_installed_packages() requires active session

**Implementation Note**: AppSelector widget may need additional method or service to fetch packages
