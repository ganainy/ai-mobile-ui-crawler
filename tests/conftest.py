"""Shared pytest fixtures for mobile-crawler tests."""

import pytest


@pytest.fixture
def sample_config():
    """Return a sample configuration dictionary for testing."""
    return {
        "ai_provider": "gemini",
        "max_crawl_steps": 15,
        "max_crawl_duration_seconds": 600,
    }
