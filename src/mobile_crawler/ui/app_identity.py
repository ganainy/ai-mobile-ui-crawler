"""Lightweight app identity helpers (icon path, taskbar id).

Kept free of heavy imports so the launcher can use them before the splash screen shows.
"""

import logging
import sys
from pathlib import Path


def get_gui_icon_path() -> str:
    """Return the absolute path to the GUI/taskbar icon."""
    return str(Path(__file__).resolve().parents[3] / "crawler_logo.ico")


def set_windows_app_user_model_id() -> None:
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
