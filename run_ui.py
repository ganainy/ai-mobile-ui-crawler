#!/usr/bin/env python3
"""
Entry point for running the Appium Crawler UI.

# Activate the virtual environment
& E:/VS-projects/appium-traverser-master-arbeit/.venv/Scripts/Activate.ps1

# Then run the UI
python run_ui.py
"""

import sys
import os

# Fix Windows encoding issues - force UTF-8 encoding
os.environ['PYTHONUTF8'] = '1'
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
from config.app_config import Config
try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    from ui.strings import RUN_UI_ERROR_PYSIDE6
    sys.exit(1)
from domain.ui_controller import CrawlerControllerWindow

# Use new logging infrastructure
from core.logging_infrastructure import (
    configure_default_logging,
    setup_logging_bridge,
    LoggingContext,
    UILogSink,
    CompactFormatter,
    LogLevel
)

def main():
    # Parse arguments first (but don't do heavy processing yet)
    parser = argparse.ArgumentParser(description="Appium Traverser")
    parser.add_argument("--provider", type=str, default=None, help="AI provider to use")
    parser.add_argument("--model", type=str, default=None, help="Model name/alias to use")
    args, unknown = parser.parse_known_args()
    
    # Create QApplication FIRST to enable GUI immediately
    # Save original argv for QApplication, then restore for later use
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]] + unknown
    app = QApplication(sys.argv)
    app.setApplicationName("Appium Traverser")
    app.setApplicationDisplayName("Appium Traverser")
    
    # Show splash screen IMMEDIATELY - before any processing
    from ui.custom_widgets import LoadingSplashScreen
    import time
    
    splash = LoadingSplashScreen()
    
    # Center the splash screen on the screen
    screen = QApplication.primaryScreen().geometry()
    splash_rect = splash.geometry()
    splash_rect.moveCenter(screen.center())
    splash.move(splash_rect.topLeft())
    
    # Make splash screen visible immediately
    splash.show()
    splash.raise_()
    splash.activateWindow()
    splash.show_message("Starting...")
    # Force multiple processEvents to ensure splash is displayed
    for _ in range(5):
        app.processEvents()
    # Small delay to ensure splash is fully rendered and visible
    time.sleep(0.1)
    app.processEvents()
    
    # Start Appium server in separate terminal if not already running
    splash.show_message("Checking Appium server...")
    app.processEvents()
    
    from infrastructure.appium_server import ensure_appium_running
    if ensure_appium_running():
        splash.show_message("Appium server ready")
    else:
        splash.show_message("Warning: Appium server failed to start")
    app.processEvents()
    
    splash.show_message("Loading configuration...")
    app.processEvents()
    
    config = Config()

    # Set provider if given
    provider = args.provider or config.get("AI_PROVIDER")
    if not provider:
        splash.show_message("Selecting AI provider...")
        app.processEvents()
        from domain.providers.registry import ProviderRegistry
        valid_providers = ProviderRegistry.get_all_names()
        from ui.strings import CLI_SELECT_PROVIDER_PROMPT
        provider = input(CLI_SELECT_PROVIDER_PROMPT.format(providers=', '.join(valid_providers))).strip().lower()
    
    from domain.providers.enums import AIProvider
    from ui.strings import CLI_ERROR_PREFIX
    try:
        # Validate provider using enum
        provider_enum = AIProvider.from_string(provider)
        config.set("AI_PROVIDER", provider_enum.value)
    except ValueError as e:
        splash.close()
        sys.exit(1)

    # Set model if given
    if args.model:
        config.set("DEFAULT_MODEL_TYPE", args.model)
    
    splash.show_message("Initializing interface...")
    app.processEvents()
    
    # Create window (this may take time)
    window = CrawlerControllerWindow()
    
    # Set up logging system
    splash.show_message("Configuring logging system...")
    app.processEvents()
    
    # 1. Configure default logging (Console + File)
    # Use log file from config if possible, or default
    # Note: Config might need to be fully loaded to get proper path
    service = configure_default_logging(
        console_level=LogLevel.INFO,
        file_level=LogLevel.DEBUG
    )
    
    # 2. Setup compatibility bridge for standard logging
    setup_logging_bridge(service, level="INFO")
    
    # 3. Setup UI Sink (replacing old set_ui_controller)
    if hasattr(window, 'log_message'):
        # Define a getter for the widget or just pass a method?
        # UILogSink expects a text_widget_getter.
        # But here we want to call window.log_message(msg, color)
        
        # We need a slight adapter for UILogSink if it only supports appending to widget
        # The existing UILogSink implementation tries 'widget.append' or 'widget.setTextColor'
        # window.log_message does custom logic.
        
        # Let's create a custom sink for the UI controller right here
        from core.logging_infrastructure import ILogSink
        
        class ControllerSink(ILogSink):
            def __init__(self, controller):
                self.controller = controller
                self.formatter = CompactFormatter()
                
            def write(self, entry):
                msg = self.formatter.format(entry)
                color = entry.level.to_color()
                self.controller.log_message(msg, color=color)
                
            def flush(self): pass
            def close(self): pass
            
        service.add_sink(ControllerSink(window))
    
    # Update splash message
    splash.show_message("Finalizing...")
    app.processEvents()
    
    # Show main window
    window.showMaximized()
    
    # Close splash screen after a short delay to ensure window is visible
    splash.finish(window)
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
