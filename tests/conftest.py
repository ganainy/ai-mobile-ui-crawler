"""Shared pytest fixtures for mobile-crawler tests."""

import pytest
from PySide6.QtWidgets import QApplication


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
