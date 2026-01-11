"""Main window for the mobile-crawler GUI application."""

import sys
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
from PySide6.QtCore import Qt, QThread, Signal

# Service imports
from mobile_crawler.infrastructure.device_detection import DeviceDetection
from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.user_config_store import UserConfigStore
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
from mobile_crawler.infrastructure.screenshot_capture import ScreenshotCapture
from mobile_crawler.infrastructure.gesture_handler import GestureHandler
from mobile_crawler.infrastructure.ai_interaction_service import AIInteractionService
from mobile_crawler.domain.action_executor import ActionExecutor
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository

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
        
        # Crawl configuration state
        self._selected_device = None
        self._selected_package = None
        self._ai_provider = None
        self._ai_model = None
        
        # Crawl execution state
        self._crawler_worker = None
        self._current_run_id = None
        self._crawler_loop = None
        
        self._setup_window()
        self._setup_menu_bar()
        self._setup_central_widget()

    def _create_services(self):
        """Create and return all service instances needed by widgets.
        
        Returns:
            dict: Dictionary of service instances
        """
        # Database and config
        db_manager = DatabaseManager()
        db_manager.create_schema()
        
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
        mobsf_manager = MobSFManager()
        
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
        }

    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle("Mobile Crawler")
        self.setMinimumSize(1024, 768)
        self.resize(1280, 960)

    def _setup_menu_bar(self):
        """Configure the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = help_menu.addAction("&About")
        about_action.triggered.connect(self._show_about)

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
        
        # Set splitter proportions (left: 25%, center: 35%, right: 40%)
        main_splitter.setSizes([250, 350, 400])
        
        main_layout.addWidget(main_splitter)
        
        # Connect signals for center panel
        self.control_panel.start_requested.connect(self._start_crawl)
        self.control_panel.pause_requested.connect(self._pause_crawl)
        self.control_panel.resume_requested.connect(self._resume_crawl)
        self.control_panel.stop_requested.connect(self._stop_crawl)
        
        # Connect QtSignalAdapter signals
        self.signal_adapter.state_changed.connect(self._on_crawl_state_changed)
        self.signal_adapter.step_started.connect(self._on_step_started)
        self.signal_adapter.action_executed.connect(self._on_action_executed)
        self.signal_adapter.step_completed.connect(self._on_step_completed)
        self.signal_adapter.crawl_completed.connect(self._on_crawl_completed)
        self.signal_adapter.ai_request_sent.connect(self.ai_monitor_panel.add_request)
        self.signal_adapter.ai_response_received.connect(self.ai_monitor_panel.add_response)
        
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
            self._current_run_id = run_id
            
            # Create crawler loop
            crawler_loop = self._create_crawler_loop(config_manager, run_id)
            self._crawler_loop = crawler_loop
            
            # Create and start worker thread
            self._crawler_worker = CrawlerWorker(crawler_loop, run_id)
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

    def _create_crawler_loop(self, config_manager: ConfigManager, run_id: int) -> CrawlerLoop:
        """Create crawler loop with all dependencies.
        
        Args:
            config_manager: Configuration manager
            run_id: Run ID
            
        Returns:
            CrawlerLoop instance
        """
        # Get the connected AppiumDriver
        appium_driver = self._services['appium_driver']
        
        state_machine = CrawlStateMachine()
        screenshot_capture = ScreenshotCapture(driver=appium_driver)
        ai_service = AIInteractionService.from_config(config_manager, event_listener=self.signal_adapter)
        gesture_handler = GestureHandler(appium_driver)
        action_executor = ActionExecutor(appium_driver, gesture_handler)
        step_log_repo = StepLogRepository(self._services['database_manager'])
        
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
            event_listeners=event_listeners
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

    def _on_crawl_completed(self, run_id: int, steps: int, duration_ms: float, reason: str) -> None:
        """Handle crawl completed event.
        
        Args:
            run_id: Run ID
            steps: Total steps completed
            duration_ms: Total duration in milliseconds
            reason: Completion reason
        """
        message = f"Crawl completed: {steps} steps in {duration_ms/1000:.1f}s - {reason}"
        if self.log_viewer:
            self.log_viewer.append_log(LogLevel.INFO, message)
        
        # Update run history
        if self.run_history_view:
            self.run_history_view._load_runs()

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
        
        # Instantiate widgets
        self.control_panel = CrawlControlPanel(self._services['crawl_controller'])
        self.control_panel.setObjectName("crawlControlPanel")
        self.stats_dashboard = StatsDashboard()
        self.stats_dashboard.setObjectName("statsDashboard")
        
        layout.addWidget(self.control_panel)
        layout.addWidget(self.stats_dashboard)
        
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
        
        # Instantiate widget
        self.run_history_view = RunHistoryView(
            self._services['run_repository'],
            self._services['report_generator'],
            self._services['mobsf_manager']
        )
        self.run_history_view.setObjectName("runHistoryView")
        
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
                                prompt: str, response: str, actions: list, error_msg):
        """Handle request to show step details in a new tab.

        Args:
            step_number: Step number
            timestamp: When interaction occurred
            success: Whether interaction succeeded
            prompt: Complete prompt text
            response: Complete response text
            actions: Parsed action details
            error_msg: Error message if failed
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
            error_message=error_msg
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

    def _show_about(self):
        """Show the about dialog."""
        from PySide6.QtWidgets import QMessageBox
        
        QMessageBox.about(
            self,
            "About Mobile Crawler",
            "AI-Powered Android Exploration Tool\n\n"
            "Version 0.1.0\n\n"
            "An automated testing tool for Android applications\n"
            "using AI vision models."
        )

    def closeEvent(self, event):
        """Handle window close event."""
        # Perform cleanup if needed
        event.accept()


def run():
    """Entry point for the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Mobile Crawler")
    app.setOrganizationName("mobile-crawler")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
