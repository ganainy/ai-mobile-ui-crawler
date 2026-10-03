"""GUI entry point that shows a splash screen before the heavy imports.

Importing ``main_window`` (PySide widgets, llama-index, drivers, ...) takes a couple
of seconds, so this module imports only PySide6 and the icon helpers, shows the
splash, and then imports the main window.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from mobile_crawler.ui.app_identity import get_gui_icon_path, set_windows_app_user_model_id


def _build_splash() -> QSplashScreen:
    width, height = 420, 220
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#1e1e2e"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    icon_pixmap = QIcon(get_gui_icon_path()).pixmap(72, 72)
    if not icon_pixmap.isNull():
        painter.drawPixmap((width - 72) // 2, 30, icon_pixmap)
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    painter.drawText(0, 120, width, 30, Qt.AlignmentFlag.AlignCenter, "Mobile Crawler")
    painter.end()

    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.showMessage(
        "Loading...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        QColor("#cdd6f4"),
    )
    return splash


def run() -> None:
    """Show the splash immediately, then load and start the main window."""
    set_windows_app_user_model_id()

    app = QApplication(sys.argv)
    app.setApplicationName("Mobile Crawler")
    app.setOrganizationName("mobile-crawler")
    app.setWindowIcon(QIcon(get_gui_icon_path()))

    splash = _build_splash()
    splash.show()
    app.processEvents()

    from mobile_crawler.ui import main_window

    main_window.run(app=app, splash=splash)


if __name__ == "__main__":
    run()
