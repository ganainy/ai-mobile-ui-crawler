"""Database management for crawler.db - crawl data storage."""

import sqlite3
from pathlib import Path
from typing import Optional

from mobile_crawler.config import get_app_data_dir


class DatabaseManager:
    """Manages SQLite database connections and schema for crawler.db."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database manager.

        Args:
            db_path: Path to database file. If None, uses default location.
        """
        if db_path is None:
            app_data_dir = get_app_data_dir()
            db_path = app_data_dir / "crawler.db"

        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory configured."""
        if self._connection is None:
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def create_schema(self):
        """Create all tables and indexes for crawler.db."""
        conn = self.get_connection()

        # runs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY,
                device_id TEXT NOT NULL,
                app_package TEXT NOT NULL,
                start_activity TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL,           -- RUNNING, STOPPED, ERROR
                ai_provider TEXT,               -- gemini, openrouter, ollama
                ai_model TEXT,                  -- model name used
                total_steps INTEGER DEFAULT 0,
                unique_screens INTEGER DEFAULT 0
            )
        """)

        # screens table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screens (
                id INTEGER PRIMARY KEY,
                composite_hash TEXT UNIQUE NOT NULL,
                visual_hash TEXT NOT NULL,
                screenshot_path TEXT,
                activity_name TEXT,
                first_seen_run_id INTEGER NOT NULL,
                first_seen_step INTEGER NOT NULL,
                FOREIGN KEY (first_seen_run_id) REFERENCES runs(id)
            )
        """)

        # step_logs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS step_logs (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL,
                step_number INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                from_screen_id INTEGER,
                to_screen_id INTEGER,
                action_type TEXT NOT NULL,      -- click, input, scroll_down, etc.
                action_description TEXT,        -- human-readable
                target_bbox_json TEXT,          -- {"top_left": [...], "bottom_right": [...]}
                input_text TEXT,                -- for input actions
                execution_success BOOLEAN NOT NULL,
                error_message TEXT,
                action_duration_ms REAL,
                ai_response_time_ms REAL,
                ai_reasoning TEXT,              -- AI's reasoning for this action
                FOREIGN KEY (run_id) REFERENCES runs(id),
                FOREIGN KEY (from_screen_id) REFERENCES screens(id),
                FOREIGN KEY (to_screen_id) REFERENCES screens(id)
            )
        """)

        # transitions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transitions (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL,
                from_screen_id INTEGER NOT NULL,
                to_screen_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                FOREIGN KEY (run_id) REFERENCES runs(id),
                FOREIGN KEY (from_screen_id) REFERENCES screens(id),
                FOREIGN KEY (to_screen_id) REFERENCES screens(id),
                UNIQUE(run_id, from_screen_id, to_screen_id, action_type)
            )
        """)

        # run_stats table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS run_stats (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL UNIQUE,

                -- Crawl Progress
                total_steps INTEGER DEFAULT 0,
                successful_steps INTEGER DEFAULT 0,
                failed_steps INTEGER DEFAULT 0,
                crawl_duration_seconds REAL,
                avg_step_duration_ms REAL,

                -- Screen Discovery
                unique_screens_visited INTEGER DEFAULT 0,
                total_screen_visits INTEGER DEFAULT 0,
                deepest_navigation_depth INTEGER DEFAULT 0,
                most_visited_screen_id INTEGER,
                most_visited_screen_count INTEGER DEFAULT 0,
                unique_activities_visited INTEGER DEFAULT 0,

                -- Action Statistics (JSON for flexibility)
                actions_by_type_json TEXT,           -- {"click": 50, "input": 10, ...}
                successful_actions_by_type_json TEXT,
                failed_actions_by_type_json TEXT,
                avg_action_duration_ms REAL,
                min_action_duration_ms REAL,
                max_action_duration_ms REAL,

                -- AI Performance
                total_ai_calls INTEGER DEFAULT 0,
                avg_ai_response_time_ms REAL,
                min_ai_response_time_ms REAL,
                max_ai_response_time_ms REAL,
                ai_timeout_count INTEGER DEFAULT 0,
                ai_error_count INTEGER DEFAULT 0,
                ai_retry_count INTEGER DEFAULT 0,
                invalid_response_count INTEGER DEFAULT 0,
                total_ai_tokens_used INTEGER,

                -- Multi-Action Batching
                multi_action_batch_count INTEGER DEFAULT 0,
                single_action_count INTEGER DEFAULT 0,
                total_batch_actions INTEGER DEFAULT 0,
                avg_batch_size REAL,
                max_batch_size INTEGER DEFAULT 0,

                -- Error & Recovery
                stuck_detection_count INTEGER DEFAULT 0,
                stuck_recovery_success INTEGER DEFAULT 0,
                app_crash_count INTEGER DEFAULT 0,
                app_relaunch_count INTEGER DEFAULT 0,
                context_loss_count INTEGER DEFAULT 0,
                context_recovery_count INTEGER DEFAULT 0,
                invalid_bbox_count INTEGER DEFAULT 0,

                -- Device & App Info
                device_model TEXT,
                android_version TEXT,
                screen_width INTEGER,
                screen_height INTEGER,
                app_version TEXT,

                -- Network & Security
                pcap_file_size_bytes INTEGER,
                pcap_packet_count INTEGER,
                mobsf_security_score REAL,
                mobsf_high_issues INTEGER DEFAULT 0,
                mobsf_medium_issues INTEGER DEFAULT 0,
                mobsf_low_issues INTEGER DEFAULT 0,
                video_file_size_bytes INTEGER,
                video_duration_seconds REAL,

                -- Coverage
                transition_count INTEGER DEFAULT 0,
                unique_transitions INTEGER DEFAULT 0,

                FOREIGN KEY (run_id) REFERENCES runs(id),
                FOREIGN KEY (most_visited_screen_id) REFERENCES screens(id)
            )
        """)

        # ai_interactions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_interactions (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL,
                step_number INTEGER NOT NULL,
                timestamp TEXT NOT NULL,               -- ISO 8601

                -- Request Details
                request_json TEXT,                     -- Full request payload
                screenshot_path TEXT,                  -- Path to screenshot sent

                -- Response Details
                response_raw TEXT,                     -- Raw AI response
                response_parsed_json TEXT,             -- Parsed/validated JSON

                -- Performance Metrics
                tokens_input INTEGER,
                tokens_output INTEGER,
                latency_ms REAL,

                -- Status
                success BOOLEAN NOT NULL DEFAULT 0,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,

                FOREIGN KEY (run_id) REFERENCES runs(id)
            )
        """)

        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_step_logs_run ON step_logs(run_id, step_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_screens_hash ON screens(composite_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transitions_run ON transitions(run_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_run_stats_run ON run_stats(run_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_interactions_run ON ai_interactions(run_id, step_number)")

        conn.commit()

    def migrate_schema(self):
        """Run database migrations if needed."""
        # For now, just create schema if it doesn't exist
        # Future: implement proper migration system
        self.create_schema()
