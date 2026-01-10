"""Main window for the mobile-crawler GUI application."""

import sys
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QMenuBar,
    QMenu,
    QApplication
)
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    """Main application window for mobile-crawler GUI."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self._setup_window()
        self._setup_menu_bar()
        self._setup_central_widget()

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
        layout = QVBoxLayout(central_widget)
        
        # Placeholder content - will be replaced with actual widgets
        layout.addStretch()
        
        self.setCentralWidget(central_widget)

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
