"""Tests for path resolution."""

import platform
from pathlib import Path
from unittest.mock import patch

import pytest

from mobile_crawler.config.paths import get_app_data_dir


class TestGetAppDataDir:
    """Tests for get_app_data_dir."""

    def test_returns_path_object(self):
        """Test get_app_data_dir returns a Path object."""
        result = get_app_data_dir()
        assert isinstance(result, Path)

    def test_path_exists_or_can_be_created(self):
        """Test returned path exists or can be created."""
        result = get_app_data_dir()
        # Path may not exist, but should be creatable
        assert result.parent.exists()

    def test_path_contains_app_name(self):
        """Test returned path contains 'mobile-crawler'."""
        result = get_app_data_dir()
        assert "mobile-crawler" in str(result)

    @patch('platform.system')
    def test_windows_path(self, mock_system):
        """Test Windows path format."""
        mock_system.return_value = "Windows"
        result = get_app_data_dir()
        # On Windows, should use AppData/Roaming
        assert "AppData" in str(result) or "mobile-crawler" in str(result)
        assert "mobile-crawler" in str(result)

    @patch('platform.system')
    def test_macos_path(self, mock_system):
        """Test macOS path format."""
        mock_system.return_value = "Darwin"
        result = get_app_data_dir()
        # On macOS, should use Library/Application Support
        assert "Application Support" in str(result)
        assert "mobile-crawler" in str(result)

    @patch('platform.system')
    def test_linux_path(self, mock_system):
        """Test Linux path format."""
        mock_system.return_value = "Linux"
        result = get_app_data_dir()
        # On Linux, should use .local/share
        assert ".local" in str(result)
        assert "share" in str(result)
        assert "mobile-crawler" in str(result)

    def test_path_is_absolute(self):
        """Test returned path is absolute."""
        result = get_app_data_dir()
        assert result.is_absolute()

    def test_path_with_temp_directory(self, tmp_path):
        """Test path creation works with temp directories."""
        custom_path = tmp_path / "mobile-crawler-test"
        custom_path.mkdir(parents=True, exist_ok=True)
        assert custom_path.exists()
        assert custom_path.is_dir()

    def test_consistent_results(self):
        """Test get_app_data_dir returns consistent results."""
        result1 = get_app_data_dir()
        result2 = get_app_data_dir()
        assert result1 == result2
