"""Tests for database.py."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from mobile_crawler.infrastructure.database import DatabaseManager


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    # Cleanup
    if path.exists():
        path.unlink()


@pytest.fixture
def db_manager(temp_db_path):
    """Create a database manager with temporary file."""
    manager = DatabaseManager(temp_db_path)
    yield manager
    manager.close()


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    def test_initialization(self, db_manager):
        """Test database manager initializes correctly."""
        assert db_manager._connection is None
        # File doesn't exist until connection is established

    def test_get_connection_creates_file(self, db_manager):
        """Test getting connection creates database file."""
        conn = db_manager.get_connection()
        assert isinstance(conn, sqlite3.Connection)
        assert db_manager.db_path.exists()

    def test_schema_creation(self, db_manager):
        """Test schema creation creates all required tables."""
        db_manager.create_schema()

        conn = db_manager.get_connection()
        cursor = conn.cursor()

        # Check all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            "runs", "screens", "step_logs", "transitions",
            "run_stats", "ai_interactions"
        }
        assert expected_tables.issubset(tables)

    def test_foreign_keys_enabled(self, db_manager):
        """Test foreign key constraints are enabled."""
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        # Check foreign keys pragma
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        assert result[0] == 1  # Should be enabled

    def test_wal_mode_enabled(self, db_manager):
        """Test WAL mode is enabled."""
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        # Check journal mode
        cursor.execute("PRAGMA journal_mode")
        result = cursor.fetchone()
        assert result[0].upper() == "WAL"

    def test_indexes_created(self, db_manager):
        """Test required indexes are created."""
        db_manager.create_schema()

        conn = db_manager.get_connection()
        cursor = conn.cursor()

        # Check indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        expected_indexes = {
            "idx_step_logs_run",
            "idx_screens_hash",
            "idx_transitions_run",
            "idx_run_stats_run",
            "idx_ai_interactions_run"
        }
        assert expected_indexes.issubset(indexes)

    def test_migrate_schema(self, db_manager):
        """Test migrate_schema calls create_schema."""
        db_manager.migrate_schema()

        conn = db_manager.get_connection()
        cursor = conn.cursor()

        # Check tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "runs" in tables

    def test_close_connection(self, db_manager):
        """Test connection can be closed."""
        conn = db_manager.get_connection()
        assert conn is not None

        db_manager.close()
        assert db_manager._connection is None
