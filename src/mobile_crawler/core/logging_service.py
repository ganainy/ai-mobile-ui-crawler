"""Logging service with multi-sink architecture."""

import sys
from typing import Dict, Any, Optional, List

from .log_sinks import LogLevel, LogSink


class LoggingService:
    """Central logging service that distributes log messages to multiple sinks."""

    def __init__(self, sinks: List[LogSink]):
        """Initialize with a list of log sinks.

        Args:
            sinks: List of LogSink instances to receive log messages.
        """
        self.sinks = sinks

    def log(self, level: LogLevel, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a message at the specified level to all sinks.

        Args:
            level: Log level
            message: Log message
            extra_data: Optional extra data to include
        """
        for sink in self.sinks:
            try:
                sink.log(level, message, extra_data)
            except Exception as e:
                # Don't let logging errors break the application
                # Log to stderr as fallback
                print(f"Logging error: {e}", file=sys.stderr)

    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a debug message."""
        self.log(LogLevel.DEBUG, message, extra_data)

    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an info message."""
        self.log(LogLevel.INFO, message, extra_data)

    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning message."""
        self.log(LogLevel.WARNING, message, extra_data)

    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an error message."""
        self.log(LogLevel.ERROR, message, extra_data)

    def action(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an action message."""
        self.log(LogLevel.ACTION, message, extra_data)