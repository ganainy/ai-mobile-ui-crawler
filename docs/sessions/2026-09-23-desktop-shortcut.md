---
author: claude
date: 2026-09-23
---
# Desktop shortcut fix

- Shortcut did nothing: `create_desktop_shortcut.ps1` searched `venv312`, `.venv`, `venv`; the project venv is `.venv312`, so it fell back to global `Python312\python.exe`, which lacks the dependencies. Added `.venv312` first.
- After that the GUI opened but console windows kept flashing: under `pythonw.exe` the process has no console, so each console child (adb, docker, scrcpy server, asyncio subprocesses) gets its own window. ~30 `subprocess` call sites plus third-party ones, so instead of editing each, `ui/main_window._hide_child_console_windows()` wraps `subprocess.Popen.__init__` to default `creationflags=CREATE_NO_WINDOW` when `GetConsoleWindow()` is 0. Explicit `creationflags` are left alone. Covers asyncio (its Windows Popen subclasses `subprocess.Popen`).
- Checked with a pythonw script: sync, asyncio and `adb devices` output still captured. `tests/ui` green. Not seen by the user yet.
