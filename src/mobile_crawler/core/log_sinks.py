"""Log sinks for multi-sink logging architecture."""

import json
import logging
import logging.handlers
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from mobile_crawler.config import get_app_data_dir
from mobile_crawler.infrastructure.database import DatabaseManager


class LogLevel(Enum):
    """Log levels for the crawler."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    ACTION = "ACTION"  # For crawler actions


class LogSink(ABC):
    """Abstract base class for log sinks."""

    @abstractmethod
    def log(self, level: LogLevel, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a message with the given level and optional extra data."""
        pass


class ConsoleSink(LogSink):
    """Sink that writes human-readable logs to stderr, with level filtering."""

    def __init__(self, min_level: LogLevel = LogLevel.INFO):
        self.min_level = min_level
        self._level_order = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.ACTION: 1,  # Same as INFO
        }

    def log(self, level: LogLevel, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        if self._level_order[level] < self._level_order[self.min_level]:
            return

        timestamp = datetime.now().isoformat()
        level_str = level.value
        extra_str = f" {extra_data}" if extra_data else ""
        print(f"[{timestamp}] {level_str}: {message}{extra_str}", file=sys.stderr)


class JSONEventSink(LogSink):
    """Sink that writes structured JSON events to stdout for CLI piping."""

    def log(self, level: LogLevel, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "message": message,
        }
        if extra_data:
            event["extra"] = extra_data

        print(json.dumps(event), file=sys.stdout)


class FileSink(LogSink):
    """Sink that writes to crawler.log with rotation."""

    def __init__(self, log_file: Path = None, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
        if log_file is None:
            from mobile_crawler.config import get_app_data_dir
            log_file = get_app_data_dir() / "crawler.log"

        self.log_file = log_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        # Set up rotating file handler
        self._handler = logging.handlers.RotatingFileHandler(
            str(log_file), maxBytes=max_bytes, backupCount=backup_count
        )
        self._handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        self._logger = logging.getLogger("crawler_file")
        self._logger.addHandler(self._handler)
        self._logger.setLevel(logging.DEBUG)

    def log(self, level: LogLevel, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        log_level_map = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.ACTION: logging.INFO,
        }

        extra_str = f" {extra_data}" if extra_data else ""
        self._logger.log(log_level_map[level], f"{message}{extra_str}")


class DatabaseSink(LogSink):
    """Sink that persists logs to the logs table in crawler.db."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        if db_manager is None:
            db_manager = DatabaseManager()
        self.db_manager = db_manager

    def log(self, level: LogLevel, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        conn = self.db_manager.get_connection()
        extra_json = json.dumps(extra_data) if extra_data else None

        conn.execute(
            "INSERT INTO logs (timestamp, level, message, extra_json) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), level.value, message, extra_json)
        )
        conn.commit()


class QLogHandler(logging.Handler):
    """Python logging handler that bridges standard logging to the UI.

    Attaches to the Python root logger (or any logger) and forwards
    all log records to a callback function, which should emit a Qt signal
    to update the UI log panel. This ensures that ALL module-level logging
    (logger.info, logger.debug, etc.) appears in the UI, not just
    event-driven messages from CrawlerLoop.
    """

    # Mapping from Python logging levels to our custom LogLevel enum
    _LEVEL_MAP = {
        logging.DEBUG: LogLevel.DEBUG,
        logging.INFO: LogLevel.INFO,
        logging.WARNING: LogLevel.WARNING,
        logging.ERROR: LogLevel.ERROR,
        logging.CRITICAL: LogLevel.ERROR,
    }

    # Third-party logger prefixes to suppress in the UI (too noisy for users).
    _SUPPRESSED_PREFIXES = (
        "httpcore.",
        "httpx.",
        "urllib3.",
        "google_genai.",
        "llama_index_instrumentation.",
        "droidrun-telemetry",
    )

    def __init__(self, callback):
        """Initialize the handler.

        Args:
            callback: Callable accepting (LogLevel, str) that routes
                      the log message to the UI (typically a Qt signal emit).
        """
        super().__init__()
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        """Forward a log record to the UI callback.

        Args:
            record: The Python log record to forward.
        """
        try:
            # Skip noisy third-party loggers that clutter the UI
            if any(record.name.startswith(p) for p in self._SUPPRESSED_PREFIXES):
                return
            message = self.format(record)
            level = self._LEVEL_MAP.get(record.levelno, LogLevel.DEBUG)
            self._callback(level, message)
        except Exception:
            # Never let logging errors break the application
            pass