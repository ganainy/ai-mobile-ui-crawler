"""Tests for configuration manager."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.infrastructure.user_config_store import UserConfigStore


class TestConfigManager:
    """Test ConfigManager."""

    def test_precedence_database(self):
        """Test that database has highest precedence."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = Path(f.name)

        try:
            user_store = UserConfigStore(db_path)
            user_store.create_schema()
            config = ConfigManager(user_store)

            # Set in DB
            config.set('test_key', 'db_value')

            # Mock env var
            with patch.dict(os.environ, {'CRAWLER_TEST_KEY': 'env_value'}):
                # Should return DB value
                assert config.get('test_key') == 'db_value'

            user_store.close()
        finally:
            db_path.unlink(missing_ok=True)

    def test_precedence_environment(self):
        """Test that environment variables override defaults."""
        config = ConfigManager()

        # Mock env var
        with patch.dict(os.environ, {'CRAWLER_TEST_KEY': 'env_value'}):
            assert config.get('test_key') == 'env_value'

    def test_precedence_defaults(self):
        """Test that defaults are used when no other source."""
        config = ConfigManager()
        assert config.get('appium_url') == 'http://localhost:4723'

    def test_precedence_fallback_to_provided_default(self):
        """Test fallback to provided default."""
        config = ConfigManager()
        assert config.get('nonexistent_key', 'fallback') == 'fallback'

    def test_environment_type_conversion(self):
        """Test environment variable type conversion."""
        config = ConfigManager()

        # Boolean
        with patch.dict(os.environ, {'CRAWLER_BOOL_KEY': 'true'}):
            assert config.get('bool_key') is True

        with patch.dict(os.environ, {'CRAWLER_BOOL_KEY': 'false'}):
            assert config.get('bool_key') is False

        # Int
        with patch.dict(os.environ, {'CRAWLER_INT_KEY': '42'}):
            assert config.get('int_key') == 42

        # Float
        with patch.dict(os.environ, {'CRAWLER_FLOAT_KEY': '3.14'}):
            assert config.get('float_key') == 3.14

        # String
        with patch.dict(os.environ, {'CRAWLER_STR_KEY': 'hello'}):
            assert config.get('str_key') == 'hello'

    def test_set_stores_in_database(self):
        """Test that set() stores value in database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = Path(f.name)

        try:
            user_store = UserConfigStore(db_path)
            user_store.create_schema()
            config = ConfigManager(user_store)

            config.set('test_key', 'test_value')

            # Should retrieve from DB
            assert config.get('test_key') == 'test_value'

            user_store.close()
        finally:
            db_path.unlink(missing_ok=True)

    def test_database_access_failure_falls_back(self):
        """Test that DB access failure falls back to env/defaults."""
        # Create config with invalid DB path
        user_store = UserConfigStore(Path('/invalid/path/db.db'))
        config = ConfigManager(user_store)

        # Should fall back to env
        with patch.dict(os.environ, {'CRAWLER_TEST_KEY': 'env_value'}):
            assert config.get('test_key') == 'env_value'