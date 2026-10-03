---
author: claude
updated: 2026-10-03
---
# GUI splash screen

User: opening the GUI (first time especially) showed nothing for a couple of seconds, no sign it had started.

Cause: `main_window.py` imports the whole app at module level (~2.5 s) before `QApplication` exists, so nothing can be shown.

Change: new `ui/launcher.py` imports only PySide6 + `ui/app_identity.py` (icon path / taskbar id helpers moved out of `main_window.py`, re-imported there under their old names), shows a `QSplashScreen` (logo, "Loading..."), then imports `main_window` and calls `run(app=, splash=)`; the splash closes via `splash.finish(window)`. `main_window.run()` still works standalone. Entry points switched to the launcher: `pyproject.toml` `mobile-crawler-gui` (needs a reinstall of the package to refresh the console script) and `create_desktop_shortcut.ps1` (re-run it to update an existing shortcut; `python -m mobile_crawler.ui.main_window` still works but has no splash).

Confirmed by the user on the desktop shortcut after it was re-created (the old shortcuts still ran `main_window`, so no splash showed at first). Offscreen check: splash builds ~1.1 s into the process, `main_window` import finishes ~2.4 s later. 
