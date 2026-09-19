"""Main window for the mobile-crawler GUI application."""

import asyncio
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QSplitterHandle,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# Import resources
from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.core.crawl_controller import CrawlController
from mobile_crawler.core.crawl_state_machine import CrawlState
from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.core.log_sinks import LogLevel, QLogHandler
from mobile_crawler.core.runtime_stats_collector import RuntimeStatsCollector
from mobile_crawler.core.stale_run_cleaner import StaleRunCleaner
from mobile_crawler.domain.guided_scenarios_generator import (
    generate_guided_scenarios,
    guided_scenarios_config_key,
    guided_scenarios_url_override_config_key,
)
from mobile_crawler.domain.models import ActionResult
from mobile_crawler.domain.providers.registry import ProviderRegistry
from mobile_crawler.domain.providers.vision_detector import VisionDetector
from mobile_crawler.domain.report_generator import ReportGenerator
from mobile_crawler.infrastructure.app_account_store import AppAccountStore
from mobile_crawler.infrastructure.database import DatabaseManager

# Service imports
from mobile_crawler.infrastructure.device_detection import DeviceDetection
from mobile_crawler.infrastructure.mobsf_docker import MobSFDockerService
from mobile_crawler.infrastructure.mobsf_manager import MobSFManager
from mobile_crawler.infrastructure.omniparser_docker import OmniParserDockerService
from mobile_crawler.infrastructure.run_repository import RunRepository
from mobile_crawler.infrastructure.run_stats_repository import RunStatsRepository
from mobile_crawler.infrastructure.screen_repository import ScreenRepository
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository
from mobile_crawler.infrastructure.step_phase_repository import StepPhaseRepository
from mobile_crawler.infrastructure.user_config_store import UserConfigStore
from mobile_crawler.ui.log_cleaner import LogCleaner
from mobile_crawler.ui.mobsf_startup_worker import MobSFStartupWorker
from mobile_crawler.ui.omniparser_startup_worker import OmniParserStartupWorker

# Signal adapter
from mobile_crawler.ui.signal_adapter import QtSignalAdapter
from mobile_crawler.ui.widgets.ai_model_selector import AIModelSelector
from mobile_crawler.ui.widgets.ai_monitor_panel import AIMonitorPanel, StepDetailWidget
from mobile_crawler.ui.widgets.app_selector import AppSelector
from mobile_crawler.ui.widgets.crawl_control_panel import CrawlControlPanel

# Widget imports
from mobile_crawler.ui.widgets.device_selector import DeviceSelector
from mobile_crawler.ui.widgets.log_viewer import LogViewer
from mobile_crawler.ui.widgets.run_history_view import RunHistoryView
from mobile_crawler.ui.widgets.settings_panel import SettingsPanel
from mobile_crawler.ui.widgets.stats_dashboard import StatsDashboard

logger = logging.getLogger(__name__)


def _get_gui_icon_path() -> str:
    """Return the absolute path to the GUI/taskbar icon."""
    return str(Path(__file__).resolve().parents[3] / "crawler_logo.ico")


def _set_windows_app_user_model_id() -> None:
    """Set Windows taskbar identity so the taskbar uses the app icon."""
    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MobileCrawler.MobileCrawler.GUI")
    except Exception:
        logging.getLogger(__name__).debug(
            "Could not set Windows AppUserModelID",
            exc_info=True,
        )


@dataclass
class CrawlStatistics:
    """Real-time statistics accumulator for active crawl session.

    Tracks crawl metrics including step counts, screen discovery,
    and AI performance. Used for real-time dashboard updates.
    """

    run_id: int
    start_time: datetime
    total_steps: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    unique_screen_hashes: set[str] = field(default_factory=set)
    total_screen_visits: int = 0
    ai_call_count: int = 0
    ai_response_times_ms: list[float] = field(default_factory=list)
    last_step_number: int = 0  # Track last seen step to avoid double counting

    # OCR timing (OCR grounding isn't used by the live pipeline — always 0/empty)
    ocr_total_time_ms: float = 0.0
    ocr_operation_count: int = 0

    # OmniParser vision-parsing timing
    omniparser_total_time_ms: float = 0.0
    omniparser_call_count: int = 0

    # Action execution timing
    action_total_time_ms: float = 0.0
    action_count: int = 0

    # Screenshot capture timing
    screenshot_total_time_ms: float = 0.0
    screenshot_count: int = 0

    # Additional crawl metrics
    last_action_type: str = ""  # most recent action type (tap, scroll, input...)
    current_step_of_max: str = ""  # e.g. "7 / 15"

    # OTel-sourced token counts (populated from StatsCollectorSpanProcessor)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    otel_latencies_ms: list[float] = field(default_factory=list)  # per-call real latencies

    # CrawlerAgent-derived metrics
    tool_call_count: int = 0  # total tool calls observed
    tool_error_count: int = 0  # tool calls that returned errors
    phase_transition_count: int = 0  # step phase transitions observed

    def avg_ai_response_time(self) -> float:
        """Calculate average AI response time in milliseconds."""
        if not self.ai_response_times_ms:
            return 0.0
        return sum(self.ai_response_times_ms) / len(self.ai_response_times_ms)

    def elapsed_seconds(self) -> float:
        """Calculate elapsed time since start in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    def screens_per_minute(self) -> float:
        """Calculate screen discovery rate per minute."""
        minutes = self.elapsed_seconds() / 60.0
        if minutes <= 0:
            return 0.0
        return len(self.unique_screen_hashes) / minutes

    def avg_ocr_time_ms(self) -> float:
        """Average OCR processing time in milliseconds."""
        if self.ocr_operation_count == 0:
            return 0.0
        return self.ocr_total_time_ms / self.ocr_operation_count

    def avg_omniparser_time_ms(self) -> float:
        """Average OmniParser vision-parsing call time in milliseconds."""
        if self.omniparser_call_count == 0:
            return 0.0
        return self.omniparser_total_time_ms / self.omniparser_call_count

    def avg_action_time_ms(self) -> float:
        """Average action execution time in milliseconds."""
        if self.action_count == 0:
            return 0.0
        return self.action_total_time_ms / self.action_count

    def avg_screenshot_time_ms(self) -> float:
        """Average screenshot capture time in milliseconds."""
        if self.screenshot_count == 0:
            return 0.0
        return self.screenshot_total_time_ms / self.screenshot_count


class CrawlerWorker(QThread):
    """Worker thread for running crawler operations."""

    finished = Signal()
    error = Signal(str)

    def __init__(self, crawler_loop, run_id: int):
        """Initialize crawler worker.

        Args:
            crawler_loop: CrawlerLoop instance
            run_id: Run ID to crawl
        """
        super().__init__()
        self.crawler_loop = crawler_loop
        self.run_id = run_id

    def run(self):
        """Run the crawler in a separate thread."""
        try:
            self.crawler_loop.run(self.run_id)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class GuidedScenariosWorker(QThread):
    """Worker thread that resolves an App Web Profile and generates a Guided Scenarios list."""

    finished = Signal(list, str)  # scenarios, warning ("" if none)
    error = Signal(str)

    def __init__(self, config_manager: ConfigManager, app_package: str, website_url_override: str | None):
        super().__init__()
        self.config_manager = config_manager
        self.app_package = app_package
        self.website_url_override = website_url_override

    def run(self):
        try:
            result = asyncio.run(
                generate_guided_scenarios(self.config_manager, self.app_package, self.website_url_override)
            )
            self.finished.emit(result.scenarios, result.warning or "")
        except Exception as e:
            self.error.emit(str(e))


class _ResettableSplitterHandle(QSplitterHandle):
    """Splitter handle that resets its splitter to defaults on double-click."""

    def mouseDoubleClickEvent(self, event):
        splitter = self.splitter()
        if isinstance(splitter, PersistedSplitter):
            splitter.reset_to_default()
        super().mouseDoubleClickEvent(event)


class PersistedSplitter(QSplitter):
    """QSplitter whose sizes are remembered across app restarts.

    Sizes are saved as proportions of the splitter's total size (not raw
    pixels), so a layout saved on one window/monitor size still restores
    sensibly on another. Saves are debounced ~500ms after dragging stops,
    so panel resizing doesn't hit the database on every mouse-move event.
    Double-clicking a handle, or calling reset_to_default(), restores the
    hardcoded default sizes.
    """

    _SAVE_DEBOUNCE_MS = 500

    def __init__(self, orientation, config_store: UserConfigStore, default_sizes: list[int], parent=None):
        super().__init__(orientation, parent)
        self._config_store = config_store
        self._default_sizes = default_sizes
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_sizes)
        self.splitterMoved.connect(lambda *_: self._save_timer.start(self._SAVE_DEBOUNCE_MS))

    def createHandle(self):
        return _ResettableSplitterHandle(self.orientation(), self)

    def _config_key(self) -> str:
        return f"ui_splitter_{self.objectName()}_sizes"

    def restore_or_default(self) -> None:
        """Apply the saved proportions, falling back to the hardcoded defaults."""
        proportions = self._config_store.get_setting(self._config_key(), default=None)
        if (
            isinstance(proportions, list)
            and len(proportions) == len(self._default_sizes)
            and all(isinstance(p, int | float) for p in proportions)
        ):
            total = sum(self._default_sizes)
            self.setSizes([max(1, round(p * total)) for p in proportions])
        else:
            self.setSizes(self._default_sizes)

    def reset_to_default(self) -> None:
        """Restore hardcoded sizes and persist them as the new saved layout."""
        self._save_timer.stop()
        self.setSizes(self._default_sizes)
        self._save_sizes()

    def flush_pending_save(self) -> None:
        """Save immediately if a debounced save is still pending (e.g. on app close)."""
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save_sizes()

    def _save_sizes(self) -> None:
        sizes = self.sizes()
        total = sum(sizes)
        if total <= 0:
            return
        proportions = [s / total for s in sizes]
        self._config_store.set_setting(self._config_key(), proportions, "json")


class MainWindow(QMainWindow):
    """Main application window for mobile-crawler GUI."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self._services = self._create_services()

        # Cleanup stale runs on startup
        stale_run_cleaner = StaleRunCleaner(self._services["database_manager"])
        stale_run_cleaner.cleanup_stale_runs()

        # Widget instances (will be created in _setup_central_widget)
        self.device_selector: DeviceSelector = None
        self.app_selector: AppSelector = None
        self.ai_selector: AIModelSelector = None
        self.control_panel: CrawlControlPanel = None
        self.log_viewer: LogViewer = None
        self.ai_monitor_panel: AIMonitorPanel = None
        self.stats_dashboard: StatsDashboard = None
        self.settings_panel: SettingsPanel = None
        self.run_history_view: RunHistoryView = None
        self.main_splitter: PersistedSplitter = None
        self.workspace_splitter: PersistedSplitter = None
        self._log_cleaner = LogCleaner()

        # Signal adapter for thread-safe event bridging
        self.signal_adapter: QtSignalAdapter = QtSignalAdapter()

        # Statistics tracking
        self._current_stats: CrawlStatistics | None = None
        self._elapsed_timer: QTimer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_elapsed_time)

        # Crawl configuration state
        self._selected_device = None
        self._selected_package = None
        self._ai_provider = None
        self._ai_model = None

        # Crawl execution state
        self._crawler_worker = None
        self._current_run_id = None
        self._crawler_loop = None

        # Guided Scenarios generation state
        self._guided_scenarios_worker = None

        # MobSF startup state
        self._mobsf_docker_service = None
        self._mobsf_startup_worker = None
        self._omniparser_docker_service = None
        self._omniparser_startup_worker = None

        # Load step-by-step preference from config store
        config_store = self._services["user_config_store"]
        self._step_by_step_enabled = config_store.get_setting("ui_step_by_step_enabled", False)

        self._setup_window()
        self._setup_central_widget()
        self._setup_python_logging()
        self._connect_statistics_signals()

    def _create_services(self):
        """Create and return all service instances needed by widgets.

        Returns:
            dict: Dictionary of service instances
        """
        # Database and config
        db_manager = DatabaseManager()
        db_manager.migrate_schema()

        user_config_store = UserConfigStore()
        user_config_store.create_schema()

        # Device and app services
        device_detection = DeviceDetection()

        # AI services
        provider_registry = ProviderRegistry(config_store=user_config_store)
        vision_detector = VisionDetector(registry=provider_registry)

        # Crawl services
        crawl_controller = CrawlController()

        # History and reporting services
        run_repository = RunRepository(db_manager)
        report_generator = ReportGenerator(db_manager)
        step_phase_repository = StepPhaseRepository(db_manager)
        session_folder_manager = SessionFolderManager()

        # Create config manager for feature managers
        from mobile_crawler.config.config_manager import ConfigManager

        config_manager = ConfigManager(user_config_store)

        # MobSF manager (initialized with config, will be fully configured when used)
        mobsf_manager = MobSFManager(
            config_manager=config_manager,
            adb_client=None,  # Will be created when needed
            session_folder_manager=session_folder_manager,
        )

        # Repository services for statistics
        step_log_repository = StepLogRepository(db_manager)
        screen_repository = ScreenRepository(db_manager)
        run_stats_repository = RunStatsRepository(db_manager)

        return {
            "device_detection": device_detection,
            "provider_registry": provider_registry,
            "vision_detector": vision_detector,
            "crawl_controller": crawl_controller,
            "user_config_store": user_config_store,
            "run_repository": run_repository,
            "step_phase_repository": step_phase_repository,
            "report_generator": report_generator,
            "mobsf_manager": mobsf_manager,
            "database_manager": db_manager,
            "step_log_repository": step_log_repository,
            "screen_repository": screen_repository,
            "run_stats_repository": run_stats_repository,
            "session_folder_manager": session_folder_manager,
        }

    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle("Mobile Crawler")
        self.setMinimumSize(1024, 768)
        self.resize(1280, 960)
        # Set window icon
        self.setWindowIcon(QIcon(_get_gui_icon_path()))

        # Hide menu bar as requested (Streamlined UI)
        self.menuBar().setVisible(False)

    def _setup_central_widget(self):
        """Configure the central widget."""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)

        config_store = self._services["user_config_store"]

        workspace_splitter = PersistedSplitter(Qt.Orientation.Vertical, config_store, [600, 170])
        workspace_splitter.setObjectName("workspaceSplitter")

        # Create main horizontal splitter for left/center/right
        main_splitter = PersistedSplitter(Qt.Orientation.Horizontal, config_store, [280, 500, 500])
        main_splitter.setObjectName("mainSplitter")
        self.main_splitter = main_splitter
        self.workspace_splitter = workspace_splitter

        # Left panel: Device, App, AI selectors, Settings
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)

        # Center panel: Crawl controls and stats
        center_panel = self._create_center_panel()
        main_splitter.addWidget(center_panel)

        # Right panel: Log viewer
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)

        # Restore saved proportions (approx 20% left, 40% center, 40% right by default)
        main_splitter.restore_or_default()

        workspace_splitter.addWidget(main_splitter)

        # Connect signals for center panel
        self.control_panel.start_requested.connect(self._start_crawl)
        self.control_panel.pause_requested.connect(self._pause_crawl)
        self.control_panel.resume_requested.connect(self._resume_crawl)
        self.control_panel.stop_requested.connect(self._stop_crawl)
        self.control_panel.step_by_step_toggled.connect(self._on_step_by_step_toggled)
        self.control_panel.next_step_requested.connect(self._on_next_step_requested)

        # Connect QtSignalAdapter signals
        self.signal_adapter.state_changed.connect(self._on_crawl_state_changed)
        self.signal_adapter.step_started.connect(self._on_step_started)
        self.signal_adapter.action_executed.connect(self._on_action_executed)
        self.signal_adapter.step_completed.connect(self._on_step_completed)
        self.signal_adapter.crawl_completed.connect(self._on_crawl_completed)
        self.signal_adapter.screen_processed.connect(self._on_screen_processed)
        self.signal_adapter.step_paused.connect(self._on_step_paused)
        self.signal_adapter.debug_log.connect(self._on_debug_log)
        self.signal_adapter.ocr_completed.connect(self._on_ocr_completed)
        self.signal_adapter.screenshot_timing.connect(self._on_screenshot_timing)
        self.signal_adapter.action_timing.connect(self._on_action_timing)
        self.signal_adapter.omniparser_timing.connect(self._on_omniparser_timing)
        self.signal_adapter.step_phase_transition.connect(self._on_step_phase_transition)
        self.signal_adapter.mobsf_finished.connect(self._on_mobsf_finished)
        if self.ai_monitor_panel and hasattr(self.signal_adapter, "ai_request_sent"):
            self.signal_adapter.ai_request_sent.connect(self.ai_monitor_panel.add_request)
            self.signal_adapter.ai_request_sent.connect(self._on_ai_request_stats)
            self.signal_adapter.ai_response_received.connect(self.ai_monitor_panel.add_response)
            self.signal_adapter.screenshot_captured.connect(self.ai_monitor_panel.add_screenshot_path)

        # Bottom panel: Run history
        bottom_panel = self._create_bottom_panel()
        workspace_splitter.addWidget(bottom_panel)
        workspace_splitter.restore_or_default()
        workspace_splitter.setStretchFactor(0, 1)
        workspace_splitter.setStretchFactor(1, 0)

        main_layout.addWidget(workspace_splitter)

        self.setCentralWidget(central_widget)

        # Auto-refresh devices on startup
        if self.device_selector:
            self.device_selector._refresh_devices()

        # Load initial data
        if self.run_history_view:
            self.run_history_view._load_runs()

        # Update start button state based on initial synced values
        self._update_start_button_state()

        # Apply initial step-by-step state to UI
        self.control_panel.set_step_by_step(self._step_by_step_enabled)

    def _start_crawl(self) -> None:
        """Start a new crawl with current configuration."""
        if not self._can_start_crawl():
            return

        try:
            # Create config manager with current settings
            config_manager = self._create_config_manager()

            # Create run record
            run = self._create_run_record()
            run_id = self._services["run_repository"].create_run(run)
            run.id = run_id  # Ensure the object has the assigned ID
            self._current_run_id = run_id

            # Initialize statistics tracking
            self._current_stats = CrawlStatistics(run_id=run_id, start_time=datetime.now())

            # Initialize runtime stats collector for persistence
            self._runtime_stats_collector = RuntimeStatsCollector(
                run_id=run_id, run_stats_repository=self._services["run_stats_repository"]
            )
            self._runtime_stats_collector.start_session()

            # Reset and configure stats dashboard
            if self.stats_dashboard:
                self.stats_dashboard.reset()
                self.stats_dashboard.set_max_steps(self.settings_panel.get_max_steps())
                self.stats_dashboard.set_max_duration(self.settings_panel.get_max_duration())
                if hasattr(self.settings_panel, "get_limit_mode"):
                    self.stats_dashboard.set_progress_mode(self.settings_panel.get_limit_mode())

            # Create crawler loop
            crawler_loop = self._create_crawler_loop(config_manager, run)
            self._crawler_loop = crawler_loop

            # Step-by-step mode is now supported with the internal crawler agent.
            # Always make it available; the UI preference persists via config.
            self.control_panel.set_step_by_step_available(True)
            # Manual pause/resume are still unimplemented stubs on CrawlerLoop
            # (they just log "not supported"), so don't expose a Pause button
            # that would look like it works but wouldn't.
            self.control_panel.set_pause_available(False)

            # Apply step-by-step mode if enabled in UI
            if self._step_by_step_enabled:
                crawler_loop.set_step_by_step_enabled(True)

            # Create and start worker thread
            self._crawler_worker = CrawlerWorker(crawler_loop, run.id)
            self._crawler_worker.finished.connect(self._on_crawl_finished)
            self._crawler_worker.error.connect(self._on_crawl_error)
            self._crawler_worker.start()

            # Update UI state
            self._update_crawl_ui_state(running=True)

        except Exception as e:
            self._show_error("Failed to start crawl", str(e))

    def _show_omniparser_starting_dialog(self, worker) -> None:
        """Show OmniParser startup status, refreshed every 3s, and announce when the server is ready."""
        service = self._omniparser_docker_service

        def status_text() -> str:
            return (
                "The local OmniParser server is still starting.\n\n"
                f"Status: {service.status if service else 'Starting...'}\n\n"
                "Hint: if you don't want to wait for it, switch the OmniParser Backend to "
                "'replicate' (remote server) in Settings."
            )

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("OmniParser Starting")
        box.setText(status_text())
        box.setStandardButtons(QMessageBox.StandardButton.Ok)

        timer = QTimer(box)

        def refresh() -> None:
            if worker.isRunning():
                box.setText(status_text())
                return
            timer.stop()
            if service is not None and service.status == "Ready":
                box.setIcon(QMessageBox.Icon.Information)
                box.setText("The local OmniParser server is ready. You can start the crawl now.")
            else:
                box.setIcon(QMessageBox.Icon.Warning)
                box.setText("OmniParser did not start. See the log for details.")

        timer.timeout.connect(refresh)
        timer.start(3000)
        box.exec()
        timer.stop()

    def _can_start_crawl(self) -> bool:
        """Check if crawl can be started with current configuration.

        Returns:
            True if all requirements are met
        """
        omniparser_worker = getattr(self, "_omniparser_startup_worker", None)
        if omniparser_worker is not None and omniparser_worker.isRunning():
            self._show_omniparser_starting_dialog(omniparser_worker)
            return False

        if not self._selected_device:
            self._show_error("No Device Selected", "Please select an Android device first.")
            return False

        if not self._selected_package:
            self._show_error("No App Selected", "Please select a target app first.")
            return False

        if not self._ai_provider or not self._ai_model:
            self._show_error("AI Not Configured", "Please select an AI provider and model first.")
            return False

        # Check API key for providers that require it
        if self._ai_provider in ["gemini", "openrouter"]:
            api_key = self._get_api_key_for_provider(self._ai_provider)
            if not api_key:
                self._show_error("API Key Missing", f"Please configure your {self._ai_provider} API key in Settings.")
                return False

        # Check PCAPdroid API key if traffic capture is enabled
        if self.settings_panel.get_enable_traffic_capture():
            pcapdroid_key = self.settings_panel.get_pcapdroid_api_key()
            if not pcapdroid_key:
                self._show_error(
                    "PCAPdroid API Key Missing",
                    "Traffic capture is enabled but PCAPdroid API key is not configured. "
                    "Please configure the API key in Settings, or disable traffic capture.",
                )
                return False

        return True

    def _create_config_manager(self) -> ConfigManager:
        """Create config manager with current UI settings.

        Returns:
            ConfigManager instance
        """
        config_manager = ConfigManager(self._services["user_config_store"])

        # Set current selections
        config_manager.set("ai_provider", self._ai_provider)
        config_manager.set("ai_model", self._ai_model)
        config_manager.set("app_package", self._selected_package)

        # Set crawl limits from settings panel
        config_manager.set("max_crawl_steps", self.settings_panel.get_max_steps())
        config_manager.set("max_crawl_duration_seconds", self.settings_panel.get_max_duration())

        # Set API keys from settings panel (they're stored as secrets, not settings)
        gemini_key = self.settings_panel.get_gemini_api_key()
        if gemini_key:
            config_manager.set("gemini_api_key", gemini_key)

        openrouter_key = self.settings_panel.get_openrouter_api_key()
        if openrouter_key:
            config_manager.set("openrouter_api_key", openrouter_key)

        # Set form fill data from settings panel
        config_manager.set("test_address", self.settings_panel.get_test_address())
        config_manager.set("test_email", self.settings_panel.get_test_email())
        config_manager.set("test_phone", self.settings_panel.get_test_phone())

        # Set screen configuration
        top_height = self.settings_panel.get_top_bar_height()
        bottom_height = self.settings_panel.get_bottom_bar_height()
        # Log to UI so user can see it's being picked up
        self.signal_adapter.on_debug_log(
            0, 0, f"UI: Setting top_bar_height to {top_height}px, bottom_bar_height to {bottom_height}px"
        )
        config_manager.set("top_bar_height", top_height)
        config_manager.set("bottom_bar_height", bottom_height)

        # Set feature flags from settings panel
        enable_traffic_capture = self.settings_panel.get_enable_traffic_capture()
        enable_video_recording = self.settings_panel.get_enable_video_recording()
        enable_mobsf_analysis = self.settings_panel.get_enable_mobsf_analysis()
        auto_run_mobsf = self.settings_panel.get_auto_run_mobsf_after_crawl()

        # Log feature flag values for debugging
        self.signal_adapter.on_debug_log(
            0,
            0,
            f"UI: Feature flags - traffic_capture={enable_traffic_capture}, video_recording={enable_video_recording}, mobsf_analysis={enable_mobsf_analysis}, auto_run_mobsf={auto_run_mobsf}",
        )

        config_manager.set("enable_traffic_capture", enable_traffic_capture)
        config_manager.set("pcapdroid_tls_decryption", bool(enable_traffic_capture))
        config_manager.set("enable_video_recording", enable_video_recording)
        config_manager.set("enable_mobsf_analysis", enable_mobsf_analysis)
        config_manager.set("auto_run_mobsf_after_crawl", auto_run_mobsf)

        # Verify settings were stored correctly by reading them back
        verified_traffic = config_manager.get("enable_traffic_capture", "NOT_FOUND")
        verified_video = config_manager.get("enable_video_recording", "NOT_FOUND")
        verified_mobsf = config_manager.get("enable_mobsf_analysis", "NOT_FOUND")
        verified_auto_run_mobsf = config_manager.get("auto_run_mobsf_after_crawl", "NOT_FOUND")
        self.signal_adapter.on_debug_log(
            0,
            0,
            f"UI: Verified DB write - traffic={verified_traffic}, video={verified_video}, mobsf={verified_mobsf}, auto_run_mobsf={verified_auto_run_mobsf}",
        )

        # Set PCAPdroid configuration (package and activity are fixed, no UI configuration needed)
        config_manager.set("pcapdroid_package", "com.emanuelef.remote_capture")
        config_manager.set("pcapdroid_activity", "com.emanuelef.remote_capture/.activities.CaptureCtrl")

        pcapdroid_api_key = self.settings_panel.get_pcapdroid_api_key()
        if pcapdroid_api_key:
            config_manager.set("pcapdroid_api_key", pcapdroid_api_key)

        # Set MobSF configuration
        mobsf_api_url = self.settings_panel.get_mobsf_api_url()
        if mobsf_api_url:
            config_manager.set("mobsf_api_url", mobsf_api_url)
        else:
            # Use default if not set in UI
            config_manager.set("mobsf_api_url", "http://localhost:8000")

        # Set DroidRun UI parser settings from settings panel
        ui_parser_mode = self.settings_panel.get_ui_parser_mode()
        config_manager.set("ui_parser_mode", ui_parser_mode)
        self.signal_adapter.on_debug_log(0, 0, f"UI: ui_parser_mode = {ui_parser_mode}")

        omniparser_backend = self.settings_panel.get_omniparser_backend()
        config_manager.set("omniparser_backend", omniparser_backend)
        self.signal_adapter.on_debug_log(0, 0, f"UI: omniparser_backend = {omniparser_backend}")

        omniparser_local_url = self.settings_panel.get_omniparser_local_url()
        config_manager.set("omniparser_local_url", omniparser_local_url)
        self.signal_adapter.on_debug_log(0, 0, f"UI: omniparser_local_url = {omniparser_local_url}")

        omniparser_timeout = self.settings_panel.get_omniparser_local_parse_timeout_seconds()
        config_manager.set("omniparser_local_parse_timeout_seconds", omniparser_timeout)
        self.signal_adapter.on_debug_log(0, 0, f"UI: omniparser_local_parse_timeout_seconds = {omniparser_timeout}")

        replicate_api_key = self.settings_panel.get_replicate_api_key()
        if replicate_api_key:
            config_manager.set("replicate_api_key", replicate_api_key)
            self.signal_adapter.on_debug_log(0, 0, f"UI: replicate_api_key set ({len(replicate_api_key)} chars)")

        # Set exploration objective from settings panel
        exploration_objective = self.settings_panel.get_exploration_objective()
        if exploration_objective:
            config_manager.set("exploration_objective", exploration_objective)
            self.signal_adapter.on_debug_log(
                0, 0, f"UI: Using custom exploration objective ({len(exploration_objective)} chars)"
            )

        # Set Tracing / Observability settings from settings panel
        enable_tracing = self.settings_panel.get_enable_tracing()
        config_manager.set("enable_tracing", enable_tracing)

        tracing_provider = self.settings_panel.get_tracing_provider()
        config_manager.set("tracing_provider", tracing_provider)

        phoenix_url = self.settings_panel.get_phoenix_url()
        config_manager.set("phoenix_url", phoenix_url)

        langfuse_host = self.settings_panel.get_langfuse_host()
        config_manager.set("langfuse_host", langfuse_host)

        langfuse_pub = self.settings_panel.get_langfuse_public_key()
        config_manager.set("langfuse_public_key", langfuse_pub)

        langfuse_sec = self.settings_panel.get_langfuse_secret_key()
        config_manager.set("langfuse_secret_key", langfuse_sec)

        self.signal_adapter.on_debug_log(
            0, 0, f"UI: Tracing settings - enabled={enable_tracing}, provider={tracing_provider}"
        )

        return config_manager

    def _create_run_record(self):
        """Create run record for the current crawl.

        Returns:
            Run instance
        """
        from datetime import datetime

        from mobile_crawler.infrastructure.run_repository import Run

        return Run(
            id=None,
            device_id=self._selected_device.device_id,
            app_package=self._selected_package,
            start_activity=None,  # Will be determined during crawl
            start_time=datetime.now(),
            end_time=None,
            status="RUNNING",
            ai_provider=self._ai_provider,
            ai_model=self._ai_model,
            total_steps=0,
            unique_screens=0,
        )

    def _create_crawler_loop(self, config_manager: ConfigManager, run: Any) -> CrawlerLoop:
        """Create crawler loop with all dependencies.

        Args:
            config_manager: Configuration manager
            run: Run object

        Returns:
            CrawlerLoop instance
        """
        event_listeners = [self.signal_adapter]

        from mobile_crawler.infrastructure.ai_interaction_repository import AIInteractionRepository

        ai_repo = AIInteractionRepository(self._services["database_manager"])

        return CrawlerLoop(
            config_manager=config_manager,
            run_repository=self._services["run_repository"],
            session_folder_manager=self._services["session_folder_manager"],
            event_listeners=event_listeners,
            ai_interaction_repository=ai_repo,
        )

    def _on_crawl_finished(self) -> None:
        """Handle crawl completion."""
        self._update_crawl_ui_state(running=False)
        self._save_run_stats()
        self._crawler_worker = None
        self._current_run_id = None
        self._crawler_loop = None
        self._runtime_stats_collector = None

    def _on_crawl_error(self, error_msg: str) -> None:
        """Handle crawl error.

        Args:
            error_msg: Error message
        """
        self._show_error("Crawl Error", error_msg)
        self._update_crawl_ui_state(running=False)
        self._save_run_stats()
        self._crawler_worker = None
        self._current_run_id = None
        self._crawler_loop = None
        self._runtime_stats_collector = None

    def _save_run_stats(self) -> None:
        """Persist the runtime stats collector to the run_stats table."""
        if not self._runtime_stats_collector:
            return

        try:
            collector = self._runtime_stats_collector

            # Fill in device/app info if available
            device_info = getattr(self, "_device_info", None)
            if device_info:
                collector.set_device_info(
                    device_id=device_info.get("serial", ""),
                    device_model=device_info.get("model", ""),
                    android_version=device_info.get("android_version", ""),
                    screen_width=device_info.get("screen_width", 0) or 0,
                    screen_height=device_info.get("screen_height", 0) or 0,
                )

            app_info = getattr(self, "_app_info", None)
            if app_info:
                collector.set_app_info(
                    app_package=app_info.get("package_name", ""),
                    app_version=app_info.get("version_name", ""),
                )

            # Record capture artifacts: scan the run's session folder for
            # any .pcap / .mp4 outputs and fold their sizes into the stats.
            try:
                session_path = None
                try:
                    repo = self._services.get("run_repository")
                    run = repo.get_run_by_id(collector._run_id) if repo else None
                    if run and run.session_path:
                        session_path = run.session_path
                except Exception as e:
                    logger.debug("Could not resolve session_path for run_stats: %s", e)

                if session_path:
                    from pathlib import Path

                    p = Path(session_path)
                    pcaps = list(p.rglob("*.pcap"))
                    if pcaps:
                        collector.record_pcap_stats(file_size_bytes=sum(f.stat().st_size for f in pcaps if f.exists()))

                    videos = list(p.rglob("*.mp4"))
                    if videos:
                        total = sum(f.stat().st_size for f in videos if f.exists())
                        # Duration: prefer manifest.json `total_duration_s` if present
                        duration_s = 0.0
                        m = p / "videos" / "manifest.json"
                        if m.exists():
                            try:
                                import json

                                with open(m, encoding="utf-8") as fh:
                                    data = json.load(fh)
                                duration_s = float(data.get("total_duration_s") or 0.0)
                                if duration_s == 0.0 and "segments" in data:
                                    duration_s = sum(
                                        float(s.get("duration_s", 0) or 0) for s in data.get("segments", [])
                                    )
                            except Exception:
                                pass
                        # Keep 0.0 when no manifest/duration — don't fabricate.
                        collector.record_video_stats(total, duration_s)
            except Exception as e:
                logger.debug("Post-crawl media scan skipped: %s", e)

            # Save via the collector's repository (set at construction time)
            collector.save()
            logger.info(f"Saved run_stats for run_id={collector._run_id}")
        except Exception as e:
            logger.error(f"Failed to save run_stats: {e}", exc_info=True)

    def _on_step_by_step_toggled(self, enabled: bool) -> None:
        """Handle step-by-step mode toggle."""
        self._step_by_step_enabled = enabled
        if self._crawler_loop:
            self._crawler_loop.set_step_by_step_enabled(enabled)

        # Save preference
        config_store = self._services["user_config_store"]
        config_store.set_setting("ui_step_by_step_enabled", enabled)

    def _on_next_step_requested(self) -> None:
        """Handle request to advance to next step."""
        if self._crawler_loop:
            self._crawler_loop.advance_step()

    def _on_step_paused(self, run_id: int, step_number: int) -> None:
        """Handle step paused event."""
        self._append_clean_log(LogLevel.INFO, f"Step {step_number} finished. Paused for review.", "ui")

    def _on_debug_log(self, run_id: int, step_number: int, message: str) -> None:
        """Handle debug log message from crawler (includes crawler agent stdout lines)."""
        self._append_clean_log(LogLevel.DEBUG, message, "debug_log")

        if self._current_stats and self._current_stats.run_id == run_id:
            self._parse_crawler_agent_progress(run_id, message)

    def _parse_droidrun_progress(self, run_id: int, message: str) -> None:
        """Parse crawler agent stdout/log messages to update all live statistics.

        The agent doesn't emit our custom signals (on_action_executed, on_ai_response_received,
        on_screen_processed) — it's a black box. We mine its stdout lines instead.

        Patterns tracked:
        - "Step N/M"                    → step counter + progress bar
        - "Manager/Executor/AppOpener/FastAgent response:" → +1 AI call
        - "✅ Execution complete:"       → +1 successful action
        - "❌ Execution complete:"       → +1 failed action
        - '{"action": "..."}' JSON      → action type for Last Action label
        - "<name>tool_name</name>"      → action type for FastAgent path
        - "<output>...</output>"        → +1 successful action (FastAgent)
        - "<error>...</error>"          → +1 failed action (FastAgent)
        """
        if not self._current_stats:
            return

        stats = self._current_stats
        updated = False

        # ── Step N/M: step progress ───────────────────────────────────────
        step_match = re.search(r"Step\s+(\d+)\s*/\s*(\d+)", message)
        if step_match:
            current_step = int(step_match.group(1))
            max_step = int(step_match.group(2))
            if current_step > stats.last_step_number:
                stats.total_steps = current_step
                stats.last_step_number = current_step
                stats.current_step_of_max = f"{current_step} / {max_step}"
                self._update_dashboard_stats()
            return  # Step lines don't need further parsing

        # ── Action outcomes ─────────────────────────────────────────────────
        # Two mutually exclusive formats, matched once so a single line
        # never double-counts an action:
        #   - CrawlerAgent executor: "✅/❌ Execution complete: <summary>"
        #   - FastAgent XML blocks:   "<output>...</output>" / "<error>...</error>"
        if "Execution complete:" in message and "✅" in message:  # executor success
            stats.successful_actions += 1
            stats.tool_call_count += 1
            updated = True
        elif "Execution complete:" in message and "❌" in message:  # executor failure
            stats.failed_actions += 1
            stats.tool_call_count += 1
            stats.tool_error_count += 1
            updated = True
        elif "<output>" in message:  # FastAgent success block
            stats.successful_actions += 1
            stats.tool_call_count += 1
            updated = True
        elif "<error>" in message and "</error>" in message:  # FastAgent error block
            stats.failed_actions += 1
            stats.tool_call_count += 1
            stats.tool_error_count += 1
            updated = True

        # ── AI call detection from crawler agent role response headers ─────────
        AI_MARKERS = (
            "Manager response:",
            "Executor response:",
            "AppOpener response:",
            "FastAgent response:",
            "StructuredOutput response:",
        )
        if any(marker in message for marker in AI_MARKERS):
            stats.ai_call_count += 1
            updated = True

        # ── Last action type from FastAgent XML: <name>tool_name</name> ───
        name_match = re.search(r"<name>([^<]+)</name>", message)
        if name_match:
            action_type = name_match.group(1)
            if action_type and action_type != stats.last_action_type:
                stats.last_action_type = action_type
                updated = True

        # ── Last action type from executor JSON payload ────────────────────
        # Executor responses include inline JSON: {"action": "click", "index": 64}
        if not name_match:
            action_match = re.search(r'"action"\s*:\s*"([^"]+)"', message)
            if action_match:
                action_type = action_match.group(1)
                if action_type and action_type != stats.last_action_type:
                    stats.last_action_type = action_type
                    updated = True

        if updated:
            self._update_dashboard_stats()

    def _parse_crawler_agent_progress(self, run_id: int, message: str) -> None:
        """Alias for the crawler-agent terminology used by newer call sites."""
        self._parse_droidrun_progress(run_id, message)

    def _pause_crawl(self) -> None:
        """Pause the current crawl."""
        if self._crawler_loop:
            self._crawler_loop.pause()

    def _resume_crawl(self) -> None:
        """Resume a paused crawl."""
        if self._crawler_loop:
            self._crawler_loop.resume()

    def _stop_crawl(self) -> None:
        """Stop the current crawl."""
        if self._crawler_loop:
            self._crawler_loop.stop()

    def _update_crawl_ui_state(self, running: bool) -> None:
        """Update UI elements based on crawl state.

        Args:
            running: True if crawl is running
        """
        # Update control panel state immediately to avoid race condition
        # with async state_changed signal from worker thread
        if self.control_panel:
            if running:
                from mobile_crawler.core.crawl_state_machine import CrawlState

                self.control_panel.update_state(CrawlState.RUNNING)
            else:
                # When not running, reset to UNINITIALIZED state
                from mobile_crawler.core.crawl_state_machine import CrawlState

                self.control_panel.update_state(CrawlState.UNINITIALIZED)

        # Disable/enable configuration widgets
        widgets_to_toggle = [self.device_selector, self.app_selector, self.ai_selector, self.settings_panel]

        for widget in widgets_to_toggle:
            if hasattr(widget, "setEnabled"):
                widget.setEnabled(not running)

        if self.settings_panel:
            self.settings_panel.set_crawl_running(running)

    def _show_error(self, title: str, message: str) -> None:
        """Show error dialog.

        Args:
            title: Dialog title
            message: Error message
        """
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(self, title, message)

    def _on_crawl_state_changed(self, run_id: int, old_state: str, new_state: str) -> None:
        """Handle crawl state changes.

        Args:
            run_id: Run ID
            old_state: Previous state string
            new_state: New state string
        """
        try:
            crawl_state = CrawlState(new_state)
            if self.control_panel:
                self.control_panel.update_state(crawl_state)
        except ValueError:
            # Invalid state string
            pass

    def _on_step_started(self, run_id: int, step_number: int) -> None:
        """Handle step started event.

        Args:
            run_id: Run ID
            step_number: Step number
        """
        message = f"Starting step {step_number}"
        self._append_clean_log(LogLevel.INFO, message, "ui")

    def _on_action_executed(self, run_id: int, step_number: int, action_index: int, result) -> None:
        """Handle action executed event.

        Args:
            run_id: Run ID
            step_number: Step number
            action_index: Action index within step
            result: ActionResult object
        """
        success_text = "SUCCESS" if result.success else "FAILED"
        message = f"Step {step_number}.{action_index}: {result.action_type} - {success_text}"
        level = LogLevel.ACTION if result.success else LogLevel.WARNING
        self._append_clean_log(level, message, "ui")

        # Accumulate action timing for statistics
        if self._current_stats and result.execution_time_ms > 0:
            self._current_stats.action_count += 1
            self._current_stats.action_total_time_ms += result.execution_time_ms
            self._update_dashboard_stats()

    def _on_ocr_completed(self, run_id: int, step_number: int, duration_ms: float, element_count: int) -> None:
        """Handle OCR completed event.

        Args:
            run_id: Run ID
            step_number: Step number
            duration_ms: OCR processing time
            element_count: Number of elements detected
        """
        # Accumulate OCR timing for statistics
        if self._current_stats:
            self._current_stats.ocr_operation_count += 1
            self._current_stats.ocr_total_time_ms += duration_ms
            self._update_dashboard_stats()

    def _on_screenshot_timing(self, run_id: int, step_number: int, duration_ms: float) -> None:
        """Handle screenshot timing event.

        Args:
            run_id: Run ID
            step_number: Step number
            duration_ms: Screenshot capture time
        """
        # Accumulate screenshot timing for statistics
        if self._current_stats:
            self._current_stats.screenshot_count += 1
            self._current_stats.screenshot_total_time_ms += duration_ms
            self._update_dashboard_stats()

    def _on_omniparser_timing(self, run_id: int, step_number: int, duration_ms: float, element_count: int) -> None:
        """Handle OmniParser vision-parsing timing event.

        Args:
            run_id: Run ID
            step_number: Step number
            duration_ms: OmniParser call duration
            element_count: Number of elements OmniParser returned
        """
        if self._current_stats and self._current_stats.run_id == run_id:
            self._current_stats.omniparser_call_count += 1
            self._current_stats.omniparser_total_time_ms += duration_ms
            self._update_dashboard_stats()

    def _on_action_timing(
        self, run_id: int, step_number: int, action_type: str, success: bool, duration_ms: float
    ) -> None:
        """Handle action timing event (real per-tool-call duration from the CrawlerAgent path).

        Args:
            run_id: Run ID
            step_number: Step number
            action_type: Tool/action name (e.g. "click", "swipe")
            success: Whether the action succeeded
            duration_ms: Wall-clock execution time
        """
        if not self._current_stats or self._current_stats.run_id != run_id:
            return

        if duration_ms > 0:
            self._current_stats.action_count += 1
            self._current_stats.action_total_time_ms += duration_ms
            self._update_dashboard_stats()

        if self._runtime_stats_collector and self._runtime_stats_collector._run_id == run_id:
            self._runtime_stats_collector.record_action(action_type, success, duration_ms)

    def _on_mobsf_finished(
        self, run_id: int, security_score: float, high_issues: int, medium_issues: int, low_issues: int
    ) -> None:
        """Handle MobSF static-analysis completion — feed results into the collector."""
        if self._runtime_stats_collector and self._runtime_stats_collector._run_id == run_id:
            self._runtime_stats_collector.record_mobsf_results(
                security_score=security_score,
                high_issues=high_issues,
                medium_issues=medium_issues,
                low_issues=low_issues,
            )

    def _on_step_phase_transition(
        self, run_id: int, step_number: int, from_phase: str, to_phase: str, duration_ms: float
    ) -> None:
        """Handle step phase transition event — count transitions for stats."""
        if self._current_stats and self._current_stats.run_id == run_id:
            self._current_stats.phase_transition_count += 1

    def _on_step_completed(self, run_id: int, step_number: int, actions_count: int, duration_ms: float) -> None:
        """Handle step completed event.

        Args:
            run_id: Run ID
            step_number: Step number
            actions_count: Number of actions in step
            duration_ms: Step duration in milliseconds
        """
        # For now, just log the completion. Full stats update would need more data
        message = f"Completed step {step_number} ({actions_count} actions, {duration_ms:.0f}ms)"
        self._append_clean_log(LogLevel.INFO, message, "ui")

        # Note: Full stats update would require accumulating data from run repository
        # For MVP, we'll keep it simple

    def _on_crawl_completed(
        self, run_id: int, steps: int, duration_ms: float, reason: str, ocr_avg_ms: float = 0.0
    ) -> None:
        """Handle crawl completed event.

        Args:
            run_id: Run ID
            steps: Total steps completed
            duration_ms: Total duration in milliseconds
            reason: Completion reason
            ocr_avg_ms: Average OCR processing time in ms
        """
        message = f"Crawl completed: {steps} steps in {duration_ms / 1000:.1f}s - {reason}"
        if ocr_avg_ms > 0:
            message += f" (OCR Avg: {ocr_avg_ms:.0f}ms)"

        self._append_clean_log(LogLevel.INFO, message, "ui")

        # Update run history
        if self.run_history_view:
            self.run_history_view._load_runs()

    def _on_screen_processed(
        self, run_id: int, step_number: int, screen_id: int, is_new: bool, visit_count: int, total_screens: int
    ) -> None:
        """Handle screen processed event.

        Args:
            run_id: Run ID
            step_number: Step number
            screen_id: ID of the processed screen
            is_new: True if this is a newly discovered screen
            visit_count: Number of times this screen has been visited
            total_screens: Total unique screens discovered
        """
        # Log screen discovery
        if is_new:
            message = f"NEW Screen #{screen_id} discovered (total: {total_screens})"
            self._append_clean_log(LogLevel.INFO, message, "ui")

        # Update stats dashboard with screen metrics
        if self._current_stats:
            # Calculate total visits (accumulate)
            self._current_stats.total_screen_visits += 1

            # Update unique screen hashes to keep stats consistent
            self._current_stats.unique_screen_hashes.add(str(screen_id))

            self._update_dashboard_stats()

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with device/app/AI selectors and settings."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Instantiate widgets
        self.device_selector = DeviceSelector(self._services["device_detection"], self._services["user_config_store"])
        self.device_selector.setObjectName("deviceSelector")
        self.app_selector = AppSelector(self._services["user_config_store"])
        self.app_selector.setObjectName("appSelector")
        self.ai_selector = AIModelSelector(
            self._services["provider_registry"], self._services["vision_detector"], self._services["user_config_store"]
        )
        self.ai_selector.setObjectName("aiModelSelector")
        self.settings_panel = SettingsPanel(self._services["user_config_store"])
        self.settings_panel.setObjectName("settingsPanel")

        # Set up API key callback for AI model selector
        self.ai_selector.set_api_key_callback(self._get_api_key_for_provider)

        # Connect signals for left panel
        self.ai_selector.model_selected.connect(self._on_model_selected)
        self.settings_panel.settings_saved.connect(self._on_settings_saved)
        self.settings_panel.omniparser_keepalive_pinged.connect(self._on_omniparser_keepalive_pinged)
        self.settings_panel.reset_layout_requested.connect(self._on_reset_layout_requested)
        self.settings_panel.delete_app_account_requested.connect(self._on_delete_app_account_requested)
        self.settings_panel.generate_guided_scenarios_requested.connect(self._on_generate_guided_scenarios_requested)
        self.device_selector.device_selected.connect(self._on_device_selected)
        self.app_selector.app_selected.connect(self._on_app_selected)

        layout.addWidget(self.device_selector, 0)
        layout.addWidget(self.app_selector, 0)
        layout.addWidget(self.ai_selector, 0)
        layout.addWidget(self.settings_panel, 1)

        return panel

    def _create_center_panel(self) -> QWidget:
        """Create the center panel with crawl controls and stats."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(2)  # Tight spacing between controls and statistics
        layout.setContentsMargins(4, 4, 4, 4)  # Minimal margins

        # Instantiate widgets
        self.control_panel = CrawlControlPanel(self._services["crawl_controller"])
        self.control_panel.setObjectName("crawlControlPanel")
        self.stats_dashboard = StatsDashboard()
        self.stats_dashboard.setObjectName("statsDashboard")

        layout.addWidget(self.control_panel, 0)
        layout.addWidget(self.stats_dashboard, 1)

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create the right panel with logs and AI monitor."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        tabs = QTabWidget()
        self.log_viewer = LogViewer()
        self.log_viewer.setObjectName("logViewer")
        self.ai_monitor_panel = AIMonitorPanel()
        self.ai_monitor_panel.setObjectName("aiMonitorPanel")
        self.ai_monitor_panel.set_timing_provider(self._services["step_phase_repository"].get_transitions_for_step)
        self.ai_monitor_panel.show_step_details.connect(self._show_ai_step_details)

        tabs.addTab(self.log_viewer, "Logs")
        tabs.addTab(self.ai_monitor_panel, "AI Monitor")

        layout.addWidget(tabs)

        return panel

    def _show_ai_step_details(
        self,
        step_number: int,
        timestamp: datetime,
        success: bool,
        calls: list,
        default_index: int,
        screenshot_path: str,
        timing_data: object,
    ) -> None:
        """Open the AI monitor detail view for a step."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Step {step_number} Details")
        dialog.setWindowFlags(
            dialog.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint
        )
        dialog.resize(1400, 900)
        layout = QVBoxLayout(dialog)
        layout.addWidget(
            StepDetailWidget(
                step_number=step_number,
                timestamp=timestamp,
                success=success,
                calls=calls,
                default_index=default_index,
                screenshot_path=screenshot_path,
                timing_data=timing_data if isinstance(timing_data, dict) else {},
            )
        )
        dialog.showMaximized()
        dialog.exec()

    def _create_bottom_panel(self) -> QWidget:
        """Create the bottom panel with run history."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 4, 4)

        # Instantiate widget
        self.run_history_view = RunHistoryView(
            self._services["run_repository"],
            self._services["report_generator"],
            self._services["mobsf_manager"],
            self._services.get("run_stats_repository"),
        )
        self.run_history_view.setObjectName("runHistoryView")
        self.run_history_view.setMinimumHeight(170)

        layout.addWidget(self.run_history_view)

        return panel

    def _on_model_selected(self, provider: str, model: str) -> None:
        """Handle AI model selection.

        Args:
            provider: Selected AI provider (e.g., 'gemini', 'openrouter')
            model: Selected model name
        """
        self._ai_provider = provider
        self._ai_model = model
        self._update_start_button_state()

    def _on_settings_saved(self) -> None:
        """Handle settings saved event.

        Validates API keys and updates start button state.
        """
        # Validate API keys based on selected provider
        if self._ai_provider:
            api_key = self._get_api_key_for_provider(self._ai_provider)
            if not api_key:
                # Show warning but don't prevent saving
                pass

        # Persist any manual edits to the Guided Scenarios list / URL override
        # for the currently selected app (same save point every other
        # per-field setting in this panel already uses).
        if self._selected_package:
            self._save_guided_scenarios_for_selected_package()
            self._save_app_account_for_selected_package()

        self._update_start_button_state()

    def _app_account_store(self) -> AppAccountStore:
        return AppAccountStore(self._services["user_config_store"])

    def _save_app_account_for_selected_package(self) -> None:
        """Persist the panel's App Account for `self._selected_package` (empty username deletes it)."""
        account = self.settings_panel.get_app_account()
        if account:
            self._app_account_store().save(self._selected_package, account)
        else:
            self._app_account_store().delete(self._selected_package)

    def _on_delete_app_account_requested(self) -> None:
        """Delete the selected app's App Account and clear the fields."""
        if self._selected_package:
            self._app_account_store().delete(self._selected_package)
        self.settings_panel.set_app_account(None)

    def _save_guided_scenarios_for_selected_package(self) -> None:
        """Persist the panel's current Guided Scenarios list + URL override for `self._selected_package`."""
        user_config_store = self._services["user_config_store"]
        user_config_store.set_setting(
            guided_scenarios_config_key(self._selected_package),
            self.settings_panel.get_guided_scenarios(),
            "json",
        )
        user_config_store.set_setting(
            guided_scenarios_url_override_config_key(self._selected_package),
            self.settings_panel.get_guided_scenarios_url_override(),
            "string",
        )

    def _load_guided_scenarios_for_selected_package(self) -> None:
        """Load the persisted Guided Scenarios list + URL override for `self._selected_package` into the panel."""
        user_config_store = self._services["user_config_store"]
        scenarios = user_config_store.get_setting(guided_scenarios_config_key(self._selected_package), default=[])
        url_override = user_config_store.get_setting(
            guided_scenarios_url_override_config_key(self._selected_package), default=""
        )
        self.settings_panel.set_guided_scenarios(scenarios if isinstance(scenarios, list) else [])
        self.settings_panel.set_guided_scenarios_url_override(url_override or "")
        self.settings_panel.set_guided_scenarios_warning(None)

    def _on_reset_layout_requested(self) -> None:
        """Restore both splitters to their default sizes and persist that."""
        if self.main_splitter:
            self.main_splitter.reset_to_default()
        if self.workspace_splitter:
            self.workspace_splitter.reset_to_default()

    def _on_device_selected(self, device) -> None:
        """Handle device selection.

        Args:
            device: AndroidDevice instance
        """
        self._selected_device = device
        if self.app_selector:
            self.app_selector.set_device_id(device.device_id if device else None)
        self.settings_panel.notify_device_changed(device.device_id if device else None)

        self._update_start_button_state()

    def _on_app_selected(self, package: str) -> None:
        """Handle app selection.

        Args:
            package: Selected app package name
        """
        self._selected_package = package
        self._load_guided_scenarios_for_selected_package()
        self.settings_panel.set_app_account(self._app_account_store().get(package))
        self._update_start_button_state()

    def _on_generate_guided_scenarios_requested(self) -> None:
        """Resolve the selected app's App Web Profile and generate a Guided Scenarios list from it."""
        if not self._selected_package:
            self.settings_panel.set_guided_scenarios_warning("Select an app first.")
            return
        if self._guided_scenarios_worker and self._guided_scenarios_worker.isRunning():
            return

        config_manager = self._create_config_manager()
        website_url_override = self.settings_panel.get_guided_scenarios_url_override()

        self.settings_panel.set_guided_scenarios_warning(None)
        self.settings_panel.set_generate_guided_scenarios_busy(True)

        self._guided_scenarios_worker = GuidedScenariosWorker(
            config_manager, self._selected_package, website_url_override or None
        )
        self._guided_scenarios_worker.finished.connect(self._on_guided_scenarios_generated)
        self._guided_scenarios_worker.error.connect(self._on_guided_scenarios_generation_error)
        self._guided_scenarios_worker.start()

    def _on_guided_scenarios_generated(self, scenarios: list, warning: str) -> None:
        """Handle a completed Guided Scenarios generation attempt."""
        self.settings_panel.set_generate_guided_scenarios_busy(False)
        self.settings_panel.set_guided_scenarios_warning(warning or None)

        if scenarios:
            # Generate always replaces the current list wholesale.
            self.settings_panel.set_guided_scenarios(scenarios)
            if self._selected_package:
                self._save_guided_scenarios_for_selected_package()

    def _on_guided_scenarios_generation_error(self, message: str) -> None:
        """Handle an unexpected failure in the Guided Scenarios worker thread."""
        self.settings_panel.set_generate_guided_scenarios_busy(False)
        self.settings_panel.set_guided_scenarios_warning(f"Failed to generate scenarios from app info: {message}")

    def _get_api_key_for_provider(self, provider: str) -> str:
        """Get API key for the specified provider.

        Args:
            provider: Provider name

        Returns:
            API key or empty string if not found
        """
        if provider == "gemini":
            return self.settings_panel.get_gemini_api_key()
        elif provider == "openrouter":
            return self.settings_panel.get_openrouter_api_key()
        elif provider == "ollama":
            # Ollama doesn't need API key
            return "ollama"
        return ""

    def _update_start_button_state(self) -> None:
        """Update the start button enabled state based on configuration.

        Start button is enabled when:
        - Device is selected
        - App package is selected
        - AI provider and model are selected
        - API key is configured (if required)
        """
        can_start = (
            self._selected_device is not None
            and self._selected_package is not None
            and self._ai_provider is not None
            and self._ai_model is not None
        )

        # Check API key for providers that require it
        if can_start and self._ai_provider in ["gemini", "openrouter"]:
            api_key = self._get_api_key_for_provider(self._ai_provider)
            can_start = can_start and bool(api_key)

        # Update the control panel
        if self.control_panel:
            self.control_panel.set_validation_passed(can_start)

    def _connect_statistics_signals(self):
        """Connect crawler events to statistics handlers."""
        self.signal_adapter.crawl_started.connect(self._on_crawl_started_stats)
        self.signal_adapter.step_completed.connect(self._on_step_completed_stats)
        self.signal_adapter.action_executed.connect(self._on_action_executed_stats)
        self.signal_adapter.ai_response_received.connect(self._on_ai_response_stats)
        self.signal_adapter.screenshot_captured.connect(self._on_screenshot_captured_stats)
        self.signal_adapter.crawl_completed.connect(self._on_crawl_completed_stats)

    def _setup_python_logging(self) -> None:
        """Bridge Python's standard logging to the UI log panel.

        Creates a QLogHandler that forwards all Python log records
        to the UI via the signal adapter's python_log signal. This
        ensures that module-level logging (logger.info, logger.debug, etc.)
        from DroidRun internals and all other modules appears in the UI,
        not just in the terminal.
        """
        self._suppress_noisy_library_loggers()

        # Connect the python_log signal to our handler slot
        self.signal_adapter.python_log.connect(self._on_python_log)

        # Create and configure the handler
        self._qlog_handler = QLogHandler(self._on_python_log_direct)
        self._qlog_handler.setLevel(logging.DEBUG)

        # Use a concise format that includes the logger name for context
        formatter = logging.Formatter("%(name)s: %(message)s")
        self._qlog_handler.setFormatter(formatter)

        # Attach to the root logger so we capture ALL module logging
        root_logger = logging.getLogger()
        root_logger.addHandler(self._qlog_handler)
        # Ensure root logger passes DEBUG+ through to our handler
        if root_logger.level > logging.DEBUG:
            root_logger.setLevel(logging.DEBUG)

    def _suppress_noisy_library_loggers(self) -> None:
        """Raise noisy library loggers to WARNING before records hit handlers."""
        silent_loggers = [
            "PIL",
            "PIL.PngImagePlugin",
            "PIL.JpegImagePlugin",
            "PIL.Image",
            "httpx",
            "openai._base_client",
            "hpack",
            "httpcore",
        ]
        for name in silent_loggers:
            logging.getLogger(name).setLevel(logging.WARNING)

    def _on_omniparser_keepalive_pinged(self, success: bool, message: str, _elapsed_seconds: float) -> None:
        """Log the result of each automatic OmniParser keep-alive ping."""
        level = LogLevel.INFO if success else LogLevel.WARNING
        self._append_clean_log(level, message, "omniparser_keepalive")

    def _append_clean_log(self, level: LogLevel, message: str, logger_name: str = "") -> None:
        """Clean a log message and append it to the UI if it remains relevant."""
        if not self.log_viewer:
            return
        cleaned = self._log_cleaner.clean(logger_name, message)
        if cleaned is not None:
            self.log_viewer.append_log(level, cleaned)

    def _on_python_log(self, level_name: str, message: str) -> None:
        """Handle Python log message forwarded via Qt signal.

        Args:
            level_name: Log level name string (e.g. "DEBUG", "INFO")
            message: Formatted log message
        """
        if not self.log_viewer:
            return

        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR,
        }
        level = level_map.get(level_name, LogLevel.DEBUG)
        logger_name = message.split(":", 1)[0] if ":" in message else "python"
        self._append_clean_log(level, message, logger_name)

        # Also parse step progress from Python logging path (DroidRun internal logs)
        # This covers the case where the message came via the logging bridge rather
        # than the stdout capture path.
        if self._current_stats:
            self._parse_crawler_agent_progress(self._current_stats.run_id, message)

    def _on_python_log_direct(self, level: LogLevel, message: str) -> None:
        """Direct callback from QLogHandler running on any thread.

        This is called from the Python logging thread (which may be
        the crawler worker thread). We emit the Qt signal here for
        thread-safe delivery to the UI.

        Args:
            level: LogLevel enum value
            message: Formatted log message
        """
        self.signal_adapter.python_log.emit(level.name, message)

    def _on_crawl_started_stats(self, run_id: int, target_package: str) -> None:
        """Initialize statistics tracking when crawl starts.

        Creates a fresh CrawlStatistics object, resets the dashboard,
        configures progress bars based on crawl mode, and starts the timer.
        """
        # Create new statistics object
        self._current_stats = CrawlStatistics(run_id=run_id, start_time=datetime.now())

        # Reset and configure dashboard display
        if self.stats_dashboard:
            self.stats_dashboard.reset()

            # Get settings and configure limits
            if self.settings_panel:
                max_steps = self.settings_panel.get_max_steps()
                max_duration = self.settings_panel.get_max_duration()
                limit_mode = self.settings_panel.get_limit_mode()

                self.stats_dashboard.set_max_steps(max_steps)
                self.stats_dashboard.set_max_duration(max_duration)
                self.stats_dashboard.set_progress_mode(limit_mode)
            else:
                # Defaults
                self.stats_dashboard.set_max_steps(100)
                self.stats_dashboard.set_max_duration(300)
                self.stats_dashboard.set_progress_mode("steps")

        # Start elapsed time timer (1-second interval)
        self._elapsed_timer.start(1000)

    def _on_step_completed_stats(self, run_id: int, step_number: int, actions_count: int, duration_ms: float) -> None:
        """Update statistics when a step completes.

        Uses step_number to accurately count steps (avoids double-counting
        from multiple actions per step).
        """
        if not self._current_stats or self._current_stats.run_id != run_id:
            return

        # Use step_number directly as total steps (more accurate than incrementing)
        self._current_stats.total_steps = step_number
        self._current_stats.last_step_number = step_number

        # Record in runtime stats collector
        if self._runtime_stats_collector and self._runtime_stats_collector._run_id == run_id:
            self._runtime_stats_collector.record_step_start()
            if actions_count > 0:
                self._runtime_stats_collector.record_step_success(duration_ms)
            else:
                self._runtime_stats_collector.record_step_failure(duration_ms, "no actions executed")

        # Update dashboard
        self._update_dashboard_stats()

    def _on_action_executed_stats(self, run_id: int, step_number: int, action_index: int, result: ActionResult) -> None:
        """Update success/failure counts when action executes.

        Tracks action success/failure rates (a step may have multiple actions).
        """
        if not self._current_stats or self._current_stats.run_id != run_id:
            return

        # Track action success vs failure
        if result.success:
            self._current_stats.successful_actions += 1
        else:
            self._current_stats.failed_actions += 1

        # Track last action type
        if hasattr(result, "action_type") and result.action_type:
            self._current_stats.last_action_type = result.action_type

        # Record in runtime stats collector
        if self._runtime_stats_collector and self._runtime_stats_collector._run_id == run_id:
            action_type = getattr(result, "action_type", "unknown") or "unknown"
            duration_ms = getattr(result, "duration_ms", 0.0) or 0.0
            self._runtime_stats_collector.record_action(action_type, result.success, duration_ms)

        # Update dashboard
        self._update_dashboard_stats()

    def _on_screenshot_captured_stats(self, run_id: int, step_number: int, screenshot_path: str) -> None:
        """Update screen discovery metrics when screenshot captured.

        Tracks unique screens by computing a perceptual hash from the screenshot.
        This allows detecting when the same screen is revisited.
        """
        if not self._current_stats or self._current_stats.run_id != run_id:
            return

        # Track the most recent screenshot path for stats dashboard overlay
        self._last_screenshot_path = screenshot_path

        # Update the screenshot display now — _last_request_data was set by
        # _on_ai_request_stats moments earlier for this same call (request_sent
        # always fires before screenshot_captured), so they're guaranteed to
        # match. Updating from _on_ai_response_stats instead would race: that
        # handler can fire for THIS call before this event updates
        # _last_screenshot_path, pairing fresh elements with the previous
        # step's screenshot.
        request_data = getattr(self, "_last_request_data", None)
        if request_data is not None:
            elements = request_data.get("ui_elements")
            vision_enabled = request_data.get("vision_enabled", True)
            status_bar_exclusion_px = request_data.get("status_bar_exclusion_px", 0)
            self.stats_dashboard.update_screenshot(screenshot_path, elements, vision_enabled, status_bar_exclusion_px)

        # Increment total visits
        self._current_stats.total_screen_visits += 1

        # Compute perceptual hash to identify unique screens
        screen_hash = None
        if screenshot_path:
            try:
                import os

                import imagehash
                from PIL import Image

                if os.path.exists(screenshot_path):
                    img = Image.open(screenshot_path)
                    screen_hash = str(imagehash.phash(img))
                    self._current_stats.unique_screen_hashes.add(screen_hash)
            except Exception:
                # If hashing fails, use step number as fallback identifier
                screen_hash = f"step_{step_number}"
                self._current_stats.unique_screen_hashes.add(screen_hash)

        # Record in runtime stats collector using the perceptual hash as an
        # in-memory dedup key (never persisted to the FK'd most_visited_screen_id).
        if self._runtime_stats_collector and self._runtime_stats_collector._run_id == run_id:
            screen_key = screen_hash or f"step_{step_number}"
            self._runtime_stats_collector.record_screen_visit(screen_id=screen_key, navigation_depth=step_number)

        # Update dashboard
        self._update_dashboard_stats()

    def _on_ai_request_stats(self, run_id: int, step_number: int, request_data: dict[str, Any]) -> None:
        """Stash request data for screenshot overlay (consumed in _on_screenshot_captured_stats).

        Emission order for a call that captures a new screenshot is always
        request_sent -> response_received -> screenshot_captured, so by the
        time screenshot_captured fires, _last_request_data already reflects
        this same call — pairing them there (not in _on_ai_response_stats)
        guarantees the screenshot and its overlay elements match.
        """
        if not self._current_stats or self._current_stats.run_id != run_id:
            return
        self._last_request_data = request_data

    def _on_ai_response_stats(self, run_id: int, step_number: int, response_data: dict[str, Any]) -> None:
        """Update AI performance metrics when response received."""
        if not self._current_stats or self._current_stats.run_id != run_id:
            return

        # Extract response time (key is 'latency_ms' from AIInteractionService)
        response_time = response_data.get("latency_ms", 0.0) or 0.0

        # Track AI calls
        self._current_stats.ai_call_count += 1
        self._current_stats.ai_response_times_ms.append(response_time)

        # Accumulate token counts (fallback when OTel span processor isn't active)
        tokens_in = response_data.get("tokens_input") or 0
        tokens_out = response_data.get("tokens_output") or 0
        if tokens_in > 0 or tokens_out > 0:
            self._current_stats.total_input_tokens += tokens_in
            self._current_stats.total_output_tokens += tokens_out

        # Record in runtime stats collector
        if self._runtime_stats_collector and self._runtime_stats_collector._run_id == run_id:
            success = response_data.get("success", True)
            self._runtime_stats_collector.record_ai_call(
                response_time_ms=response_time, tokens_used=tokens_in + tokens_out, success=success
            )

            # Record retries / invalid responses (each validation retry = one invalid response)
            retry_count = response_data.get("retry_count", 0) or 0
            for _ in range(retry_count):
                self._runtime_stats_collector.record_ai_retry()
                self._runtime_stats_collector.record_invalid_response()

            # Track call type for per-type success rates
            call_type = response_data.get("call_type")
            if call_type:
                self._runtime_stats_collector.record_ai_call_type(call_type, success)

            # Track vision vs non-vision call ratio
            vision_enabled = response_data.get("vision_enabled", True)
            if vision_enabled:
                self._runtime_stats_collector.record_vision_call()
            else:
                self._runtime_stats_collector.record_non_vision_call()

            # Track stuck (navigation loop) detections and recoveries
            loop_detected = bool(response_data.get("loop_detected", False))
            if loop_detected:
                self._runtime_stats_collector.record_stuck_detection()
                self._loop_detected_prev = True
            else:
                if getattr(self, "_loop_detected_prev", False):
                    self._runtime_stats_collector.record_stuck_recovery(success=True)
                self._loop_detected_prev = False

        # Update dashboard
        self._update_dashboard_stats()

    def _update_dashboard_stats(self) -> None:
        """Update dashboard display from current statistics.

        Reads values from the in-memory CrawlStatistics object and
        pushes them to the StatsDashboard widget.
        """
        if not self._current_stats or not self.stats_dashboard:
            return

        stats = self._current_stats

        # Prefer OTel real per-call latencies; fall back to recorded response times only
        if stats.otel_latencies_ms:
            avg_ai_ms = sum(stats.otel_latencies_ms) / len(stats.otel_latencies_ms)
        else:
            avg_ai_ms = stats.avg_ai_response_time()

        self.stats_dashboard.update_stats(
            total_steps=stats.total_steps,
            successful_steps=stats.successful_actions,
            failed_steps=stats.failed_actions,
            unique_screens=len(stats.unique_screen_hashes),
            total_visits=stats.total_screen_visits,
            screens_per_minute=stats.screens_per_minute(),
            ai_calls=stats.ai_call_count,
            avg_ai_response_time_ms=avg_ai_ms,
            duration_seconds=stats.elapsed_seconds(),
            action_avg_ms=stats.avg_action_time_ms(),
            ocr_avg_ms=stats.avg_ocr_time_ms(),
            screenshot_avg_ms=stats.avg_screenshot_time_ms(),
            omniparser_avg_ms=stats.avg_omniparser_time_ms(),
            last_action=stats.last_action_type,
            step_progress=stats.current_step_of_max or str(stats.total_steps),
            total_input_tokens=stats.total_input_tokens,
            total_output_tokens=stats.total_output_tokens,
            success_rate=(
                round(stats.successful_actions / max(stats.successful_actions + stats.failed_actions, 1) * 100)
            ),
            tool_calls_per_step=(round(stats.tool_call_count / max(stats.total_steps, 1), 1)),
            tool_error_count=stats.tool_error_count,
            phase_transition_count=stats.phase_transition_count,
        )

    def _update_elapsed_time(self) -> None:
        """Timer callback to update elapsed time (called every 1 second).

        Triggers a full dashboard update to refresh time-dependent metrics.
        Never overwrites total_steps — that would corrupt real data from
        step events or DroidRun log parsing.
        """
        if not self._current_stats:
            return

        # Pull latest OTel token/latency data from the active crawl. Only
        # adopt it once OTel has actually captured something — otherwise an
        # inactive/unsupported span processor (0/0 snapshot) would stomp the
        # token counts already accumulated per-call in _on_ai_response_stats.
        if self._crawler_loop:
            span_stats = self._crawler_loop.get_span_stats()
            if span_stats is not None and (span_stats.total_input_tokens > 0 or span_stats.total_output_tokens > 0):
                self._current_stats.total_input_tokens = span_stats.total_input_tokens
                self._current_stats.total_output_tokens = span_stats.total_output_tokens
                self._current_stats.otel_latencies_ms = span_stats.llm_latencies_ms

        self._update_dashboard_stats()

    def _on_crawl_completed_stats(self, run_id: int, total_steps: int, total_duration_ms: float, reason: str) -> None:
        """Finalize statistics when crawl completes.

        Stops the timer and preserves final statistics on the dashboard.
        Uses reconciliation strategy: prefer best available source.
        """
        self._elapsed_timer.stop()

        if not self._current_stats:
            return

        # Always trust the completion event's step count over our running estimate
        self._current_stats.total_steps = total_steps

        # Parse action stats from reason suffix if present
        # Format: "reason | successful=X failed=Y total=Z"
        suffix_successful = 0
        suffix_failed = 0
        if " | " in reason:
            try:
                stats_part = reason.split(" | ", 1)[1]
                parsed = {}
                for item in stats_part.split():
                    if "=" in item:
                        k, v = item.split("=", 1)
                        parsed[k] = v
                if "successful" in parsed:
                    suffix_successful = int(parsed["successful"])
                if "failed" in parsed:
                    suffix_failed = int(parsed["failed"])
            except (ValueError, IndexError, AttributeError):
                pass

        # Reconciliation: prefer live-parsed stats when suffix reports zeros
        # but live parser already captured non-zero action data
        live_total = self._current_stats.successful_actions + self._current_stats.failed_actions
        suffix_total = suffix_successful + suffix_failed

        if suffix_total > 0 and suffix_total >= live_total:
            # Suffix has real data and is at least as complete — use it
            self._current_stats.successful_actions = suffix_successful
            self._current_stats.failed_actions = suffix_failed
        # else: keep live-parsed stats (they're already non-zero or both are zero)

        self._update_dashboard_stats()
        self._current_stats = None

    def start_mobsf_if_enabled(self) -> None:
        """Start the MobSF Docker container in the background if analysis is enabled.

        Only runs when the persisted ``enable_mobsf_analysis`` setting is on. The
        orchestration runs on a worker thread so the UI stays responsive during
        container startup or a first-time image pull.
        """
        if not self.settings_panel.get_enable_mobsf_analysis():
            return

        docker_service = MobSFDockerService()
        self._mobsf_docker_service = docker_service

        worker = MobSFStartupWorker(docker_service)
        worker.result.connect(self._on_mobsf_startup_result)
        self._mobsf_startup_worker = worker
        worker.start()

    def _on_mobsf_startup_result(self, ok: bool, message: str, started_by_gui: bool) -> None:
        """Handle the MobSF startup worker result: log it and warn if it failed."""
        if self._mobsf_docker_service is not None:
            self._mobsf_docker_service.started_by_gui = started_by_gui

        level = LogLevel.INFO if ok else LogLevel.WARNING
        self._append_clean_log(level, f"MobSF: {message}", "mobsf")

        if not ok:
            QMessageBox.warning(
                self,
                "MobSF Unavailable",
                f"MobSF static analysis could not be started:\n\n{message}",
            )

    def start_omniparser_if_enabled(self) -> None:
        """Start the local OmniParser Docker stack in the background if it will be used.

        Only runs when the parser mode uses OmniParser and the backend is ``local``.
        """
        if self.settings_panel.get_ui_parser_mode() == "accessibility":
            return
        if self.settings_panel.get_omniparser_backend() != "local":
            return

        docker_service = OmniParserDockerService(self.settings_panel.get_omniparser_local_url())
        self._omniparser_docker_service = docker_service

        worker = OmniParserStartupWorker(docker_service)
        worker.result.connect(self._on_omniparser_startup_result)
        self._omniparser_startup_worker = worker
        worker.start()

    def _on_omniparser_startup_result(self, ok: bool, message: str, started_by_gui: bool) -> None:
        """Handle the OmniParser startup worker result: log it and warn if it failed."""
        if self._omniparser_docker_service is not None:
            self._omniparser_docker_service.started_by_gui = started_by_gui

        level = LogLevel.INFO if ok else LogLevel.WARNING
        self._append_clean_log(level, f"OmniParser: {message}", "omniparser")

        if not ok:
            QMessageBox.warning(
                self,
                "OmniParser Unavailable",
                f"Local OmniParser could not be started:\n\n{message}",
            )

    def _maybe_prompt_docker_stop(self) -> None:
        """Offer to stop the managed Docker containers (MobSF, OmniParser) that are still running.

        Shows one dialog with a checkbox per running container. "Keep Running" leaves
        everything up; "Stop Selected" stops only the checked ones.
        """
        candidates = []
        for label, attr in (("MobSF", "_mobsf_docker_service"), ("OmniParser", "_omniparser_docker_service")):
            service = getattr(self, attr, None)
            if service is None and attr == "_omniparser_docker_service":
                # Not started this session (e.g. parser mode/backend differed at
                # launch), but the stack may still be up from an earlier run.
                try:
                    service = OmniParserDockerService(self.settings_panel.get_omniparser_local_url())
                except Exception:
                    continue
            if service is None:
                continue
            try:
                if service.is_running():
                    candidates.append((label, service))
            except Exception:
                continue

        if not candidates:
            return

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Docker containers still running")
        box.setText("Select the containers to stop. Leave all unchecked to keep them running.")

        container = QWidget()
        layout = QVBoxLayout(container)
        checkboxes = []
        for label, service in candidates:
            checkbox = QCheckBox(f"Stop {label}")
            layout.addWidget(checkbox)
            checkboxes.append((checkbox, service))
        box.layout().addWidget(container, box.layout().rowCount(), 0, 1, box.layout().columnCount())

        keep_btn = box.addButton("Keep Running", QMessageBox.ButtonRole.RejectRole)
        stop_btn = box.addButton("Stop Selected", QMessageBox.ButtonRole.AcceptRole)
        box.setDefaultButton(keep_btn)

        # "Stop Selected" is only meaningful when at least one box is checked.
        stop_btn.setEnabled(False)

        def _update_stop_enabled() -> None:
            stop_btn.setEnabled(any(cb.isChecked() for cb, _ in checkboxes))

        for checkbox, _ in checkboxes:
            checkbox.toggled.connect(_update_stop_enabled)

        box.exec()

        if box.clickedButton() is stop_btn:
            to_stop = [
                (label, svc) for (cb, svc), (label, _) in zip(checkboxes, candidates, strict=False) if cb.isChecked()
            ]
            self._stop_containers_with_progress(to_stop)

    def _stop_containers_with_progress(self, services: list) -> None:
        """Stop the given (label, service) pairs off the UI thread behind a busy dialog."""
        import threading

        from PySide6.QtCore import QEventLoop
        from PySide6.QtWidgets import QProgressDialog

        names = ", ".join(label for label, _ in services)
        progress = QProgressDialog(f"Stopping {names}...", None, 0, 0, self)
        progress.setWindowTitle("Stopping containers")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.setAutoClose(False)
        progress.setAutoReset(False)

        def _work() -> None:
            for _, service in services:
                try:
                    service.stop()
                except Exception:
                    logger.warning("Failed to stop container", exc_info=True)

        thread = threading.Thread(target=_work, daemon=True)
        loop = QEventLoop()
        poll = QTimer()
        poll.setInterval(100)

        def _check() -> None:
            if not thread.is_alive():
                poll.stop()
                loop.quit()

        poll.timeout.connect(_check)
        thread.start()
        poll.start()
        progress.show()
        loop.exec()
        progress.close()

    def closeEvent(self, event):
        """Handle window close event."""
        self._maybe_prompt_docker_stop()

        try:
            if self.settings_panel:
                self.settings_panel.stop_keepalive()

            # Flush any debounced splitter-size save so a resize right before
            # quitting isn't lost.
            if self.main_splitter:
                self.main_splitter.flush_pending_save()
            if self.workspace_splitter:
                self.workspace_splitter.flush_pending_save()

            # Stop crawler if running
            if self._crawler_loop:
                self._crawler_loop.stop()

            # Wait for worker thread to finish safely
            worker = getattr(self, "_crawler_worker", None)
            if worker and hasattr(worker, "isRunning") and worker.isRunning():
                worker.quit()
                if not worker.wait(2000):  # Wait up to 2s
                    worker.terminate()
                    worker.wait()

            # Wait briefly for the MobSF startup worker to avoid a running-thread warning
            startup_worker = getattr(self, "_mobsf_startup_worker", None)
            if startup_worker and startup_worker.isRunning():
                if not startup_worker.wait(10000):
                    startup_worker.terminate()
                    startup_worker.wait()

            omniparser_worker = getattr(self, "_omniparser_startup_worker", None)
            if omniparser_worker and omniparser_worker.isRunning():
                if not omniparser_worker.wait(10000):
                    omniparser_worker.terminate()
                    omniparser_worker.wait()

            # Wait briefly for the Guided Scenarios worker to avoid a running-thread warning
            guided_scenarios_worker = getattr(self, "_guided_scenarios_worker", None)
            if guided_scenarios_worker and guided_scenarios_worker.isRunning():
                if not guided_scenarios_worker.wait(2000):
                    guided_scenarios_worker.terminate()
                    guided_scenarios_worker.wait()
        except Exception:
            # Silently fail on close errors
            pass

        event.accept()


def run():
    """Entry point for the GUI application."""
    _set_windows_app_user_model_id()

    app = QApplication(sys.argv)
    app.setApplicationName("Mobile Crawler")
    app.setOrganizationName("mobile-crawler")

    # Set application icon for taskbar using absolute file path
    # IMPORTANT: Must be set BEFORE creating the window for Windows taskbar
    app.setWindowIcon(QIcon(_get_gui_icon_path()))

    # Create window after setting the app icon
    window = MainWindow()
    window.showMaximized()

    # The taskbar button is sometimes created before Windows picks up the icon
    # (intermittent blank logo). Re-apply it once the native window exists.
    def _reapply_icon():
        icon = QIcon(_get_gui_icon_path())
        app.setWindowIcon(icon)
        window.setWindowIcon(icon)

    QTimer.singleShot(0, _reapply_icon)
    QTimer.singleShot(1000, _reapply_icon)

    window.start_mobsf_if_enabled()
    window.start_omniparser_if_enabled()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
