"""Placeholder test to verify pytest setup works."""

import pytest

from mobile_crawler import __version__


@pytest.mark.unit
def test_version_exists():
    """Verify package version is defined."""
    assert __version__ is not None
    assert __version__ == "0.1.0"


@pytest.mark.unit
def test_sample_config_fixture(sample_config):
    """Verify the sample_config fixture works."""
    assert sample_config["ai_provider"] == "gemini"
    assert sample_config["max_crawl_steps"] == 15
    assert sample_config["max_crawl_duration_seconds"] == 600
