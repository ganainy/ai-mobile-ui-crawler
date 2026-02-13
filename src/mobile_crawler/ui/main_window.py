"""Main window for the mobile-crawler GUI application."""

import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, List, Dict, Any
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QMenuBar,
    QMenu,
    QTabWidget,
    QTabBar,
    QApplication
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QIcon

# Service imports
from mobile_crawler.infrastructure.device_detection import DeviceDetection
from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.user_config_store import UserConfigStore
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager
from mobile_crawler.infrastructure.run_repository import RunRepository
from mobile_crawler.infrastructure.mobsf_manager import MobSFManager
from mobile_crawler.domain.providers.registry import ProviderRegistry
from mobile_crawler.domain.providers.vision_detector import VisionDetector
from mobile_crawler.domain.report_generator import ReportGenerator
from mobile_crawler.core.crawl_controller import CrawlController
from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.core.crawl_state_machine import CrawlStateMachine, CrawlState
from mobile_crawler.core.log_sinks import LogLevel
from mobile_crawler.core.stale_run_cleaner import StaleRunCleaner
from mobile_crawler.infrastructure.screenshot_capture import ScreenshotCapture
from mobile_crawler.infrastructure.gesture_handler import GestureHandler
from mobile_crawler.infrastructure.ai_interaction_service import AIInteractionService
from mobile_crawler.domain.action_executor import ActionExecutor
from mobile_crawler.domain.screen_tracker import ScreenTracker
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository
from mobile_crawler.infrastructure.screen_repository import ScreenRepository
from mobile_crawler.domain.models import ActionResult
from mobile_crawler.infrastructure.mailosaur.service import MailosaurService
from mobile_crawler.infrastructure.mailosaur.models import MailosaurConfig

# Widget imports
from mobile_crawler.ui.widgets.device_selector import DeviceSelector
from mobile_crawler.ui.widgets.app_selector import AppSelector
from mobile_crawler.ui.widgets.ai_model_selector import AIModelSelector
from mobile_crawler.ui.widgets.crawl_control_panel import CrawlControlPanel
from mobile_crawler.ui.widgets.log_viewer import LogViewer
from mobile_crawler.ui.widgets.stats_dashboard import StatsDashboard
from mobile_crawler.ui.widgets.settings_panel import SettingsPanel
from mobile_crawler.ui.widgets.run_history_view import RunHistoryView
from mobile_crawler.ui.widgets.ai_monitor_panel import AIMonitorPanel, StepDetailWidget

# Signal adapter
from mobile_crawler.ui.signal_adapter import QtSignalAdapter

# Import resources
import mobile_crawler.ui.resources.resources_rc


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
    unique_screen_hashes: Set[str] = field(default_factory=set)
    total_screen_visits: int = 0
    ai_call_count: int = 0
    ai_response_times_ms: List[float] = field(default_factory=list)
    last_step_number: int = 0  # Track last seen step to avoid double counting
    
    # OCR timing
    ocr_total_time_ms: float = 0.0
    ocr_operation_count: int = 0
    
    # Action execution timing
    action_total_time_ms: float = 0.0
    action_count: int = 0
    
    # Screenshot capture timing
    screenshot_total_time_ms: float = 0.0
    screenshot_count: int = 0
    
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


class MainWindow(QMainWindow):
    """Main application window for mobile-crawler GUI."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self._services = self._create_services()
        
        # Cleanup stale runs on startup
        stale_run_cleaner = StaleRunCleaner(self._services['database_manager'])
        stale_run_cleaner.cleanup_stale_runs()
        
        # Widget instances (will be created in _setup_central_widget)
        self.device_selector: DeviceSelector = None
        self.app_selector: AppSelector = None
        self.ai_selector: AIModelSelector = None
        self.control_panel: CrawlControlPanel = None
        self.log_viewer: LogViewer = None
        self.stats_dashboard: StatsDashboard = None
        self.settings_panel: SettingsPanel = None
        self.run_history_view: RunHistoryView = None
        self.ai_monitor_panel: AIMonitorPanel = None
        
        # Signal adapter for thread-safe event bridging
        self.signal_adapter: QtSignalAdapter = QtSignalAdapter()
        
        # Statistics tracking
        self._current_stats: Optional[CrawlStatistics] = None
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
        
        # Load step-by-step preference from config store
        config_store = self._services['user_config_store']
        self._step_by_step_enabled = config_store.get_setting('ui_step_by_step_enabled', False)
        
        self._setup_window()
        self._setup_central_widget()
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
        appium_driver = AppiumDriver("dummy-device")  # Will be updated when device is selected
        
        # AI services
        provider_registry = ProviderRegistry()
        vision_detector = VisionDetector()
        
        # Crawl services
        crawl_controller = CrawlController()
        
        # History and reporting services
        run_repository = RunRepository(db_manager)
        report_generator = ReportGenerator(db_manager)
        session_folder_manager = SessionFolderManager()
        
        # Create config manager for feature managers
        from mobile_crawler.config.config_manager import ConfigManager
        config_manager = ConfigManager(user_config_store)
        
        # MobSF manager (initialized with config, will be fully configured when used)
        mobsf_manager = MobSFManager(
            config_manager=config_manager,
            adb_client=None,  # Will be created when needed
            session_folder_manager=session_folder_manager
        )
        
        # Repository services for statistics
        step_log_repository = StepLogRepository(db_manager)
        screen_repository = ScreenRepository(db_manager)
        
        return {
            'device_detection': device_detection,
            'appium_driver': appium_driver,
            'provider_registry': provider_registry,
            'vision_detector': vision_detector,
            'crawl_controller': crawl_controller,
            'user_config_store': user_config_store,
            'run_repository': run_repository,
            'report_generator': report_generator,
            'mobsf_manager': mobsf_manager,
            'database_manager': db_manager,
            'step_log_repository': step_log_repository,
            'screen_repository': screen_repository,
            'session_folder_manager': session_folder_manager,
        }

    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle("Mobile Crawler")
        self.setMinimumSize(1024, 768)
        self.resize(1280, 960)
        # Set window icon
        self.setWindowIcon(QIcon(":/resources/crawler_logo.ico"))
        
        # Hide menu bar as requested (Streamlined UI)
        self.menuBar().setVisible(False)

    def _setup_central_widget(self):
        """Configure the central widget."""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Create main horizontal splitter for left/center/right
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Device, App, AI selectors, Settings
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Center panel: Crawl controls and stats
        center_panel = self._create_center_panel()
        main_splitter.addWidget(center_panel)
        
        # Right panel: Log viewer
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter proportions (approx 20% left, 40% center, 40% right)
        main_splitter.setSizes([280, 500, 500])
        
        main_layout.addWidget(main_splitter)
        
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
        self.signal_adapter.ai_request_sent.connect(self.ai_monitor_panel.add_request)
        self.signal_adapter.screenshot_captured.connect(self.ai_monitor_panel.add_screenshot_path)
        self.signal_adapter.ai_response_received.connect(self._on_ai_response_received)
        self.signal_adapter.screen_processed.connect(self._on_screen_processed)
        self.signal_adapter.step_paused.connect(self._on_step_paused)
        self.signal_adapter.debug_log.connect(self._on_debug_log)
        self.signal_adapter.ocr_completed.connect(self._on_ocr_completed)
        self.signal_adapter.screenshot_timing.connect(self._on_screenshot_timing)
        
        # Bottom panel: Run history
        bottom_panel = self._create_bottom_panel()
        main_layout.addWidget(bottom_panel)
        
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
            # Update Appium driver with the selected app package and reconnect
            appium_driver = self._services['appium_driver']
            appium_driver.disconnect()
            appium_driver.app_package = self._selected_package
            appium_driver.connect()
            
            # Create config manager with current settings
            config_manager = self._create_config_manager()
            
            # Create run record
            run = self._create_run_record()
            run_id = self._services['run_repository'].create_run(run)
            run.id = run_id  # Ensure the object has the assigned ID
            self._current_run_id = run_id
            
            # Initialize statistics tracking
            self._current_stats = CrawlStatistics(
                run_id=run_id,
                start_time=datetime.now()
            )
            
            # Reset and configure stats dashboard
            if self.stats_dashboard:
                self.stats_dashboard.reset()
                self.stats_dashboard.set_max_steps(self.settings_panel.get_max_steps())
                self.stats_dashboard.set_max_duration(self.settings_panel.get_max_duration())
            
            # Create crawler loop
            crawler_loop = self._create_crawler_loop(config_manager, run)
            self._crawler_loop = crawler_loop
            
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

    def _can_start_crawl(self) -> bool:
        """Check if crawl can be started with current configuration.
        
        Returns:
            True if all requirements are met
        """
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
        if self._ai_provider in ['gemini', 'openrouter']:
            api_key = self._get_api_key_for_provider(self._ai_provider)
            if not api_key:
                self._show_error("API Key Missing", f"Please configure your {self._ai_provider} API key in Settings.")
                return False
        
        # Check PCAPdroid API key if traffic capture is enabled
        if self.settings_panel.get_enable_traffic_capture():
            pcapdroid_key = self.settings_panel.get_pcapdroid_api_key()
            if not pcapdroid_key:
                self._show_error("PCAPdroid API Key Missing", 
                    "Traffic capture is enabled but PCAPdroid API key is not configured. "
                    "Please configure the API key in Settings, or disable traffic capture.")
                return False
        
        return True

    def _create_config_manager(self) -> ConfigManager:
        """Create config manager with current UI settings.
        
        Returns:
            ConfigManager instance
        """
        config_manager = ConfigManager(self._services['user_config_store'])
        
        # Set current selections
        config_manager.set('ai_provider', self._ai_provider)
        config_manager.set('ai_model', self._ai_model)
        config_manager.set('app_package', self._selected_package)
        
        # Set crawl limits from settings panel
        config_manager.set('max_crawl_steps', self.settings_panel.get_max_steps())
        config_manager.set('max_crawl_duration_seconds', self.settings_panel.get_max_duration())
        
        # Set API keys from settings panel (they're stored as secrets, not settings)
        gemini_key = self.settings_panel.get_gemini_api_key()
        if gemini_key:
            config_manager.set('gemini_api_key', gemini_key)
        
        openrouter_key = self.settings_panel.get_openrouter_api_key()
        if openrouter_key:
            config_manager.set('openrouter_api_key', openrouter_key)
        
        # Set test credentials from settings panel
        config_manager.set('test_username', self.settings_panel.get_test_username())
        config_manager.set('test_password', self.settings_panel.get_test_password())
        config_manager.set('test_email', self.settings_panel.get_test_email())
        config_manager.set('mailosaur_api_key', self.settings_panel.get_mailosaur_api_key())
        config_manager.set('mailosaur_server_id', self.settings_panel.get_mailosaur_server_id())

        # Set screen configuration
        top_height = self.settings_panel.get_top_bar_height()
        # Log to UI so user can see it's being picked up
        self.signal_adapter.on_debug_log(0, 0, f"UI: Setting top_bar_height to {top_height}px")
        config_manager.set('top_bar_height', top_height)
        
        # Set feature flags from settings panel
        enable_traffic_capture = self.settings_panel.get_enable_traffic_capture()
        enable_video_recording = self.settings_panel.get_enable_video_recording()
        enable_mobsf_analysis = self.settings_panel.get_enable_mobsf_analysis()
        
        # Log feature flag values for debugging
        self.signal_adapter.on_debug_log(0, 0, f"UI: Feature flags - traffic_capture={enable_traffic_capture}, video_recording={enable_video_recording}, mobsf_analysis={enable_mobsf_analysis}")
        
        config_manager.set('enable_traffic_capture', enable_traffic_capture)
        config_manager.set('enable_video_recording', enable_video_recording)
        config_manager.set('enable_mobsf_analysis', enable_mobsf_analysis)
        
        # Verify settings were stored correctly by reading them back
        verified_traffic = config_manager.get('enable_traffic_capture', 'NOT_FOUND')
        verified_video = config_manager.get('enable_video_recording', 'NOT_FOUND')
        verified_mobsf = config_manager.get('enable_mobsf_analysis', 'NOT_FOUND')
        self.signal_adapter.on_debug_log(0, 0, f"UI: Verified DB write - traffic={verified_traffic}, video={verified_video}, mobsf={verified_mobsf}")
        
        # Set PCAPdroid configuration (package and activity are fixed, no UI configuration needed)
        config_manager.set('pcapdroid_package', 'com.emanuelef.remote_capture')
        config_manager.set('pcapdroid_activity', 'com.emanuelef.remote_capture/.activities.CaptureCtrl')
        
        pcapdroid_api_key = self.settings_panel.get_pcapdroid_api_key()
        if pcapdroid_api_key:
            config_manager.set('pcapdroid_api_key', pcapdroid_api_key)
        
        # Set MobSF configuration
        mobsf_api_url = self.settings_panel.get_mobsf_api_url()
        if mobsf_api_url:
            config_manager.set('mobsf_api_url', mobsf_api_url)
        else:
            # Use default if not set in UI
            config_manager.set('mobsf_api_url', 'http://localhost:8000')
        
        mobsf_api_key = self.settings_panel.get_mobsf_api_key()
        if mobsf_api_key:
            config_manager.set('mobsf_api_key', mobsf_api_key)
        
        return config_manager

    def _create_run_record(self):
        """Create run record for the current crawl.
        
        Returns:
            Run instance
        """
        from mobile_crawler.infrastructure.run_repository import Run
        from datetime import datetime
        
        return Run(
            id=None,
            device_id=self._selected_device.device_id,
            app_package=self._selected_package,
            start_activity=None,  # Will be determined during crawl
            start_time=datetime.now(),
            end_time=None,
            status='RUNNING',
            ai_provider=self._ai_provider,
            ai_model=self._ai_model,
            total_steps=0,
            unique_screens=0
        )

    def _create_crawler_loop(self, config_manager: ConfigManager, run: Any) -> CrawlerLoop:
        """Create crawler loop with all dependencies.
        
        Args:
            config_manager: Configuration manager
            run: Run object
            
        Returns:
            CrawlerLoop instance
        """
        run_id = run.id
        # Get the connected AppiumDriver
        appium_driver = self._services['appium_driver']
        
        state_machine = CrawlStateMachine()
        screenshot_capture = ScreenshotCapture(
            driver=appium_driver, 
            run_id=run_id,
            session_folder_manager=self._services['session_folder_manager']
        )
        ai_service = AIInteractionService.from_config(config_manager, event_listener=self.signal_adapter)
        gesture_handler = GestureHandler(appium_driver)
        
        # Initialize MailosaurService for ActionExecutor
        import os
        mailosaur_api_key = os.environ.get('MAILOSAUR_API_KEY') or config_manager.get('mailosaur_api_key')
        mailosaur_server_id = os.environ.get('MAILOSAUR_SERVER_ID') or config_manager.get('mailosaur_server_id')
        
        mailosaur_service = None
        if mailosaur_api_key and mailosaur_server_id:
            mailosaur_config = MailosaurConfig(
                api_key=mailosaur_api_key,
                server_id=mailosaur_server_id
            )
            mailosaur_service = MailosaurService(config=mailosaur_config)
        
        action_executor = ActionExecutor(
            appium_driver, 
            gesture_handler, 
            mailosaur_service=mailosaur_service,
            test_email=config_manager.get('test_email')
        )
        step_log_repo = StepLogRepository(self._services['database_manager'])
        
        # Get screen deduplication configuration
        screen_similarity_threshold = config_manager.get("screen_similarity_threshold", 12)
        use_perceptual_hashing = config_manager.get("use_perceptual_hashing", True)
        screen_tracker = ScreenTracker(
            self._services['database_manager'],
            screen_similarity_threshold=screen_similarity_threshold,
            use_perceptual_hashing=use_perceptual_hashing
        )
        
        # Attach signal adapter as event listener
        event_listeners = [self.signal_adapter]
        
        return CrawlerLoop(
            crawl_state_machine=state_machine,
            screenshot_capture=screenshot_capture,
            ai_interaction_service=ai_service,
            action_executor=action_executor,
            step_log_repository=step_log_repo,
            run_repository=self._services['run_repository'],
            config_manager=config_manager,
            appium_driver=appium_driver,
            screen_tracker=screen_tracker,
            session_folder_manager=self._services['session_folder_manager'],
            event_listeners=event_listeners,
            top_bar_height=config_manager.get('top_bar_height', 0)
        )

    def _on_crawl_finished(self) -> None:
        """Handle crawl completion."""
        self._update_crawl_ui_state(running=False)
        self._crawler_worker = None
        self._current_run_id = None
        self._crawler_loop = None

    def _on_crawl_error(self, error_msg: str) -> None:
        """Handle crawl error.
        
        Args:
            error_msg: Error message
        """
        self._show_error("Crawl Error", error_msg)
        self._update_crawl_ui_state(running=False)
        self._crawler_worker = None
        self._current_run_id = None
        self._crawler_loop = None

    def _on_step_by_step_toggled(self, enabled: bool) -> None:
        """Handle step-by-step mode toggle."""
        self._step_by_step_enabled = enabled
        if self._crawler_loop:
            self._crawler_loop.set_step_by_step_enabled(enabled)
            
        # Save preference
        config_store = self._services['user_config_store']
        config_store.set_setting('ui_step_by_step_enabled', enabled)

    def _on_next_step_requested(self) -> None:
        """Handle request to advance to next step."""
        if self._crawler_loop:
            self._crawler_loop.advance_step()

    def _on_step_paused(self, run_id: int, step_number: int) -> None:
        """Handle step paused event."""
        if self.log_viewer:
            self.log_viewer.append_log(LogLevel.INFO, f"Step {step_number} finished. Paused for review.")
        
        if self.right_tab_widget:
            self.right_tab_widget.setCurrentIndex(1)  # Index 1 is AI Monitor

    def _on_debug_log(self, run_id: int, step_number: int, message: str) -> None:
        """Handle debug log message from crawler."""
        if self.log_viewer:
            self.log_viewer.append_log(LogLevel.DEBUG, message)

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
        # Control panel state is updated via signal_adapter.state_changed
        # Disable/enable configuration widgets
        widgets_to_toggle = [
            self.device_selector,
            self.app_selector, 
            self.ai_selector,
            self.settings_panel
        ]
        
        for widget in widgets_to_toggle:
            if hasattr(widget, 'setEnabled'):
                widget.setEnabled(not running)

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
        if self.log_viewer:
            self.log_viewer.append_log(LogLevel.INFO, message)

    def _on_ai_response_received(self, run_id: int, step_number: int, response_data: dict) -> None:
        """Handle AI response received event.
        
        Args:
            run_id: Run ID
            step_number: Step number
            response_data: Response data dictionary
        """
        # Forward to AI monitor panel only if it contains full response data
        # Summary responses from CrawlerLoop are ignored by the Monitor
        if self.ai_monitor_panel:
            if self.ai_monitor_panel._is_full_response(response_data):
                self.ai_monitor_panel.add_response(run_id, step_number, response_data)

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
        if self.log_viewer:
            self.log_viewer.append_log(level, message)
        
        # Accumulate action timing for statistics
        if self._current_stats and result.execution_time_ms > 0:
            self._current_stats.action_count += 1
            self._current_stats.action_total_time_ms += result.execution_time_ms
            # Update stats dashboard
            if self.stats_dashboard:
                self.stats_dashboard.update_stats(action_avg_ms=self._current_stats.avg_action_time_ms())

    def _on_ocr_completed(
        self, run_id: int, step_number: int, duration_ms: float, element_count: int
    ) -> None:
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
            # Update stats dashboard
            if self.stats_dashboard:
                self.stats_dashboard.update_stats(ocr_avg_ms=self._current_stats.avg_ocr_time_ms())

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
            # Update stats dashboard
            if self.stats_dashboard:
                self.stats_dashboard.update_stats(screenshot_avg_ms=self._current_stats.avg_screenshot_time_ms())

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
        if self.log_viewer:
            self.log_viewer.append_log(LogLevel.INFO, message)
        
        # Note: Full stats update would require accumulating data from run repository
        # For MVP, we'll keep it simple

    def _on_crawl_completed(self, run_id: int, steps: int, duration_ms: float, reason: str, ocr_avg_ms: float = 0.0) -> None:
        """Handle crawl completed event.
        
        Args:
            run_id: Run ID
            steps: Total steps completed
            duration_ms: Total duration in milliseconds
            reason: Completion reason
            ocr_avg_ms: Average OCR processing time in ms
        """
        message = f"Crawl completed: {steps} steps in {duration_ms/1000:.1f}s - {reason}"
        if ocr_avg_ms > 0:
            message += f" (OCR Avg: {ocr_avg_ms:.0f}ms)"
            
        if self.log_viewer:
            self.log_viewer.append_log(LogLevel.INFO, message)
        
        # Update run history
        if self.run_history_view:
            self.run_history_view._load_runs()

    def _on_screen_processed(
        self,
        run_id: int,
        step_number: int,
        screen_id: int,
        is_new: bool,
        visit_count: int,
        total_screens: int
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
            if self.log_viewer:
                self.log_viewer.append_log(LogLevel.INFO, message)
        
        # Update stats dashboard with screen metrics
        if self.stats_dashboard and self._current_stats:
            # Calculate total visits (accumulate)
            self._current_stats.total_screen_visits += 1
            
            # Update unique screen hashes to keep stats consistent
            self._current_stats.unique_screen_hashes.add(str(screen_id))
            
            # Calculate screens per minute
            elapsed_minutes = self._current_stats.elapsed_seconds() / 60.0
            screens_per_min = total_screens / elapsed_minutes if elapsed_minutes > 0 else 0.0
            
            # Update the dashboard
            self.stats_dashboard.update_stats(
                total_steps=step_number,
                successful_steps=self._current_stats.successful_actions,
                failed_steps=self._current_stats.failed_actions,
                unique_screens=total_screens,
                total_visits=self._current_stats.total_screen_visits,
                screens_per_minute=screens_per_min,
                ai_calls=self._current_stats.ai_call_count,
                avg_ai_response_time_ms=self._current_stats.avg_ai_response_time(),
                duration_seconds=self._current_stats.elapsed_seconds()
            )

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with device/app/AI selectors and settings."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Instantiate widgets
        self.device_selector = DeviceSelector(
            self._services['device_detection'],
            self._services['user_config_store']
        )
        self.device_selector.setObjectName("deviceSelector")
        self.app_selector = AppSelector(
            self._services['appium_driver'],
            self._services['user_config_store']
        )
        self.app_selector.setObjectName("appSelector")
        self.ai_selector = AIModelSelector(
            self._services['provider_registry'],
            self._services['vision_detector'],
            self._services['user_config_store']
        )
        self.ai_selector.setObjectName("aiModelSelector")
        self.settings_panel = SettingsPanel(self._services['user_config_store'])
        self.settings_panel.setObjectName("settingsPanel")
        
        # Set up API key callback for AI model selector
        self.ai_selector.set_api_key_callback(self._get_api_key_for_provider)
        
        # Connect signals for left panel
        self.ai_selector.model_selected.connect(self._on_model_selected)
        self.settings_panel.settings_saved.connect(self._on_settings_saved)
        self.device_selector.device_selected.connect(self._on_device_selected)
        self.app_selector.app_selected.connect(self._on_app_selected)
        
        # Sync initial state from widgets that loaded persisted values
        # (signals were emitted before connections were made)
        if self.app_selector.current_package():
            self._selected_package = self.app_selector.current_package()
        
        layout.addWidget(self.device_selector)
        layout.addWidget(self.app_selector)
        layout.addWidget(self.ai_selector)
        layout.addWidget(self.settings_panel)
        
        return panel

    def _create_center_panel(self) -> QWidget:
        """Create the center panel with crawl controls and stats."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(2)  # Tight spacing between controls and statistics
        layout.setContentsMargins(4, 4, 4, 4)  # Minimal margins
        
        # Instantiate widgets
        self.control_panel = CrawlControlPanel(self._services['crawl_controller'])
        self.control_panel.setObjectName("crawlControlPanel")
        self.stats_dashboard = StatsDashboard()
        self.stats_dashboard.setObjectName("statsDashboard")
        
        layout.addWidget(self.control_panel, 0)
        layout.addWidget(self.stats_dashboard, 1)
        
        return panel

    def _create_right_panel(self) -> QWidget:
        """Create the right panel with tabbed log viewer and AI monitor."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Create tab widget and store reference
        self.right_tab_widget = QTabWidget()

        # Instantiate widgets
        self.log_viewer = LogViewer()
        self.log_viewer.setObjectName("logViewer")

        self.ai_monitor_panel = AIMonitorPanel()
        self.ai_monitor_panel.setObjectName("aiMonitorPanel")

        # Connect show step details signal
        self.ai_monitor_panel.show_step_details.connect(self._on_show_step_details)

        # Add tabs
        self.right_tab_widget.addTab(self.log_viewer, "Logs")
        self.right_tab_widget.addTab(self.ai_monitor_panel, "AI Monitor")

        # Enable closeable tabs but hide close button on main tabs
        self.right_tab_widget.setTabsClosable(True)
        self.right_tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.right_tab_widget.tabBar().setTabButton(1, QTabBar.ButtonPosition.RightSide, None)
        self.right_tab_widget.tabCloseRequested.connect(self._on_tab_close_requested)

        layout.addWidget(self.right_tab_widget)

        return panel

    def _create_bottom_panel(self) -> QWidget:
        """Create the bottom panel with run history."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 4, 4)
        
        # Instantiate widget
        self.run_history_view = RunHistoryView(
            self._services['run_repository'],
            self._services['report_generator'],
            self._services['mobsf_manager']
        )
        self.run_history_view.setObjectName("runHistoryView")
        self.run_history_view.setMinimumHeight(280)  # US4: Increase visibility
        
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
        self._update_start_button_state()

    def _on_show_step_details(self, step_number: int, timestamp, success: bool,
                                prompt: str, response: str, actions: list, error_msg, screenshot_path: str = None):
        """Handle request to show step details in a new tab.

        Args:
            step_number: Step number
            timestamp: When interaction occurred
            success: Whether interaction succeeded
            prompt: Complete prompt text
            response: Complete response text
            actions: Parsed action details
            error_msg: Error message if failed
            screenshot_path: Path to screenshot file
        """
        from datetime import datetime
        
        # Create detail widget
        detail_widget = StepDetailWidget(
            step_number=step_number,
            timestamp=timestamp if isinstance(timestamp, datetime) else datetime.now(),
            success=success,
            full_prompt=prompt,
            full_response=response,
            parsed_actions=actions or [],
            error_message=error_msg,
            screenshot_path=screenshot_path
        )

        # Add as new tab
        tab_title = f"Step {step_number}"
        tab_index = self.right_tab_widget.addTab(detail_widget, tab_title)
        
        # Switch to the new tab
        self.right_tab_widget.setCurrentIndex(tab_index)

    def _on_tab_close_requested(self, index: int):
        """Handle tab close request.

        Args:
            index: Tab index to close
        """
        # Don't allow closing the main tabs (Logs and AI Monitor)
        if index > 1:  # Only allow closing detail tabs
            self.right_tab_widget.removeTab(index)

    def _on_device_selected(self, device) -> None:
        """Handle device selection.
        
        Args:
            device: AndroidDevice instance
        """
        self._selected_device = device
        
        # Update the AppiumDriver with the selected device and connect
        if device:
            appium_driver = self._services['appium_driver']
            # Disconnect any existing session
            appium_driver.disconnect()
            # Update device ID and connect
            appium_driver.device_id = device.device_id
            try:
                appium_driver.connect()
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Appium Connection Failed",
                    f"Failed to connect to device via Appium:\n\n{e}\n\n"
                    "Please ensure:\n"
                    "1. Appium server is running (npx appium -p 4723)\n"
                    "2. The device is connected and authorized\n"
                    "3. USB debugging is enabled"
                )
        
        self._update_start_button_state()

    def _on_app_selected(self, package: str) -> None:
        """Handle app selection.
        
        Args:
            package: Selected app package name
        """
        self._selected_package = package
        self._update_start_button_state()

    def _get_api_key_for_provider(self, provider: str) -> str:
        """Get API key for the specified provider.
        
        Args:
            provider: Provider name
            
        Returns:
            API key or empty string if not found
        """
        if provider == 'gemini':
            return self.settings_panel.get_gemini_api_key()
        elif provider == 'openrouter':
            return self.settings_panel.get_openrouter_api_key()
        elif provider == 'ollama':
            # Ollama doesn't need API key
            return 'ollama'
        return ''

    def _update_start_button_state(self) -> None:
        """Update the start button enabled state based on configuration.
        
        Start button is enabled when:
        - Device is selected
        - App package is selected  
        - AI provider and model are selected
        - API key is configured (if required)
        """
        can_start = (
            self._selected_device is not None and
            self._selected_package is not None and
            self._ai_provider is not None and
            self._ai_model is not None
        )
        
        # Check API key for providers that require it
        if can_start and self._ai_provider in ['gemini', 'openrouter']:
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
        self.signal_adapter.crawl_completed.connect(self._on_crawl_completed_stats)

    def _on_crawl_started_stats(self, run_id: int, target_package: str) -> None:
        """Initialize statistics tracking when crawl starts.
        
        Creates a fresh CrawlStatistics object, resets the dashboard,
        configures progress bars based on crawl mode, and starts the timer.
        """
        # Create new statistics object
        self._current_stats = CrawlStatistics(
            run_id=run_id,
            start_time=datetime.now()
        )
        
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
                self.stats_dashboard.set_progress_mode('steps')
        
        # Start elapsed time timer (1-second interval)
        self._elapsed_timer.start(1000)

    def _on_step_completed_stats(self, run_id: int, step_number: int, 
                                 actions_count: int, duration_ms: float) -> None:
        """Update statistics when a step completes.
        
        Uses step_number to accurately count steps (avoids double-counting
        from multiple actions per step).
        """
        if not self._current_stats or self._current_stats.run_id != run_id:
            return
        
        # Use step_number directly as total steps (more accurate than incrementing)
        self._current_stats.total_steps = step_number
        self._current_stats.last_step_number = step_number
        
        # Update dashboard
        self._update_dashboard_stats()

    def _on_action_executed_stats(self, run_id: int, step_number: int, 
                                   action_index: int, result: ActionResult) -> None:
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
        
        # Update dashboard
        self._update_dashboard_stats()

    def _on_screenshot_captured_stats(self, run_id: int, step_number: int, 
                                       screenshot_path: str) -> None:
        """Update screen discovery metrics when screenshot captured.
        
        Tracks unique screens by computing a perceptual hash from the screenshot.
        This allows detecting when the same screen is revisited.
        """
        if not self._current_stats or self._current_stats.run_id != run_id:
            return
        
        # Increment total visits
        self._current_stats.total_screen_visits += 1
        
        # Compute perceptual hash to identify unique screens
        if screenshot_path:
            try:
                import imagehash
                from PIL import Image
                import os
                
                if os.path.exists(screenshot_path):
                    img = Image.open(screenshot_path)
                    screen_hash = str(imagehash.phash(img))
                    self._current_stats.unique_screen_hashes.add(screen_hash)
            except Exception:
                # If hashing fails, use step number as fallback identifier
                self._current_stats.unique_screen_hashes.add(f"step_{step_number}")
        
        # Update dashboard
        self._update_dashboard_stats()

    def _on_ai_response_stats(self, run_id: int, step_number: int, 
                              response_data: Dict[str, Any]) -> None:
        """Update AI performance metrics when response received."""
        if not self._current_stats or self._current_stats.run_id != run_id:
            return
        
        # Extract response time (key is 'latency_ms' from AIInteractionService)
        response_time = response_data.get('latency_ms', 0.0) or 0.0
        
        # Track AI calls
        self._current_stats.ai_call_count += 1
        self._current_stats.ai_response_times_ms.append(response_time)
        
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
        
        self.stats_dashboard.update_stats(
            total_steps=stats.total_steps,
            successful_steps=stats.successful_actions,
            failed_steps=stats.failed_actions,
            unique_screens=len(stats.unique_screen_hashes),
            total_visits=stats.total_screen_visits,
            screens_per_minute=stats.screens_per_minute(),
            ai_calls=stats.ai_call_count,
            avg_ai_response_time_ms=stats.avg_ai_response_time(),
            duration_seconds=stats.elapsed_seconds()
        )

    def _update_elapsed_time(self) -> None:
        """Timer callback to update elapsed time (called every 1 second).
        
        Triggers a full dashboard update to refresh time-dependent metrics.
        """
        if not self._current_stats:
            return
        
        # Full dashboard update includes elapsed time
        self._update_dashboard_stats()

    def _on_crawl_completed_stats(self, run_id: int, total_steps: int, 
                                   total_duration_ms: float, reason: str) -> None:
        """Finalize statistics when crawl completes.
        
        Stops the timer and preserves final statistics on the dashboard.
        Does NOT clear statistics immediately to prevent UI flicker.
        """
        # Stop timer
        self._elapsed_timer.stop()
        
        # Perform one final update with current in-memory values
        # This ensures the final state is displayed correctly
        if self._current_stats:
            # Use the total_steps from the completion event for accuracy
            self._current_stats.total_steps = total_steps
            self._update_dashboard_stats()
        
        # Clear statistics object (but dashboard retains last values)
        self._current_stats = None

    def _query_final_statistics(self, run_id: int) -> Dict[str, Any]:
        """Query database for accurate final statistics.
        
        Returns:
            Dictionary with all statistics fields for update_stats()
        """
        step_repo = self._services.get('step_log_repository')
        screen_repo = self._services.get('screen_repository')
        
        # Query step statistics
        step_stats = step_repo.get_step_statistics(run_id) if step_repo else {}
        
        # Query screen counts
        unique_screens = screen_repo.count_unique_screens_for_run(run_id) if screen_repo else 0
        total_visits = step_repo.count_screen_visits_for_run(run_id) if step_repo else 0
        
        # Query AI metrics
        ai_stats = step_repo.get_ai_statistics(run_id) if step_repo else {}
        
        # Calculate derived metrics
        duration = (datetime.now() - self._current_stats.start_time).total_seconds() if self._current_stats else 0
        screens_per_min = (unique_screens / (duration / 60.0)) if duration > 0 else 0.0
        
        return {
            'total_steps': step_stats.get('total_steps', 0),
            'successful_steps': step_stats.get('successful_steps', 0),
            'failed_steps': step_stats.get('failed_steps', 0),
            'unique_screens': unique_screens,
            'total_visits': total_visits,
            'screens_per_minute': screens_per_min,
            'ai_calls': ai_stats.get('ai_calls', 0),
            'avg_ai_response_time_ms': ai_stats.get('avg_response_time_ms', 0.0),
            'duration_seconds': duration
        }

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Stop crawler if running
            if self._crawler_loop:
                self._crawler_loop.stop()
                
            # Wait for worker thread to finish safely
            worker = getattr(self, '_crawler_worker', None)
            if worker and hasattr(worker, 'isRunning') and worker.isRunning():
                worker.quit()
                if not worker.wait(2000): # Wait up to 2s
                    worker.terminate()
                    worker.wait()
        except Exception:
            # Silently fail on close errors
            pass
                
        event.accept()


def run():
    """Entry point for the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Mobile Crawler")
    app.setOrganizationName("mobile-crawler")
    
    # Set application icon for taskbar using absolute file path
    # IMPORTANT: Must be set BEFORE creating the window for Windows taskbar
    import os
    icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'crawler_logo.ico')
    app.setWindowIcon(QIcon(icon_path))
    
    # Create window after setting the app icon
    window = MainWindow()
    window.showMaximized()
    
    sys.exit(app.exec())
