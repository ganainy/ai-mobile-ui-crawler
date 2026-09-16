"""Shared pytest fixtures for mobile-crawler tests."""

import os

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

# Run the GUI offscreen so no test ever flashes a window on screen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _silence_modal_dialogs(monkeypatch):
    """Neutralize modal dialogs so no UI test blocks on a manual button press.

    Tests that assert on specific dialog content override these stubs inside
    their own test bodies (which run after this fixture).
    """
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)


@pytest.fixture(scope="session")
def qt_app():
    """Create QApplication instance for all UI tests.

    This fixture is created at session scope to ensure QApplication
    exists for all UI tests. PySide6 requires exactly one QApplication
    instance to exist for widgets to work properly.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_config():
    """Return a sample configuration dictionary for testing."""
    return {
        "ai_provider": "gemini",
        "max_crawl_steps": 15,
        "max_crawl_duration_seconds": 600,
    }
