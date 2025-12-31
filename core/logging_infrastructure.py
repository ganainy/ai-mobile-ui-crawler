"""
Centralized Logging Infrastructure
====================================

This module provides a clean, centralized logging system following SOLID principles
and clean architecture patterns. It separates concerns, provides clear interfaces,
and makes logging testable and maintainable.

Architecture Layers:
1. Core Domain - LogEntry, LogLevel (pure domain objects)
2. Ports (Interfaces) - ILogSink, ILogFormatter, ILogFilter
3. Adapters - ConsoleLogSink, FileLogSink, UILogSink
4. Application Services - LoggingService, LoggingContext
"""

import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol
from contextlib import contextmanager


# ============================================================================
# DOMAIN LAYER - Pure domain objects with no external dependencies
# ============================================================================

class LogLevel(IntEnum):
    """Standard logging levels."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    
    @classmethod
    def from_string(cls, level: str) -> 'LogLevel':
        """Convert string to LogLevel."""
        mapping = {
            'DEBUG': cls.DEBUG,
            'INFO': cls.INFO,
            'WARNING': cls.WARNING,
            'ERROR': cls.ERROR,
            'CRITICAL': cls.CRITICAL,
        }
        return mapping.get(level.upper(), cls.INFO)
    
    def to_color(self) -> str:
        """Get UI color for this log level."""
        colors = {
            LogLevel.DEBUG: 'gray',
            LogLevel.INFO: 'white',
            LogLevel.WARNING: 'yellow',
            LogLevel.ERROR: 'red',
            LogLevel.CRITICAL: 'magenta',
        }
        return colors.get(self, 'white')


@dataclass(frozen=True)
class LogEntry:
    """Immutable log entry representing a single log message."""
    message: str
    level: LogLevel
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    
    def format(self, formatter: 'ILogFormatter') -> str:
        """Format this log entry using the provided formatter."""
        return formatter.format(self)
    
    def with_context(self, **kwargs) -> 'LogEntry':
        """Create a new log entry with additional context."""
        new_context = {**self.context, **kwargs}
        return LogEntry(
            message=self.message,
            level=self.level,
            timestamp=self.timestamp,
            context=new_context,
            source=self.source
        )


# ============================================================================
# PORT LAYER - Interfaces defining contracts
# ============================================================================

class ILogFormatter(ABC):
    """Interface for formatting log entries."""
    
    @abstractmethod
    def format(self, entry: LogEntry) -> str:
        """Format a log entry into a string."""
        pass


class ILogFilter(ABC):
    """Interface for filtering log entries."""
    
    @abstractmethod
    def should_log(self, entry: LogEntry) -> bool:
        """Determine if a log entry should be logged."""
        pass


class ILogSink(ABC):
    """Interface for log output destinations."""
    
    @abstractmethod
    def write(self, entry: LogEntry) -> None:
        """Write a log entry to this sink."""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered log entries."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the sink and release resources."""
        pass


# ============================================================================
# ADAPTER LAYER - Concrete implementations
# ============================================================================

class StandardFormatter(ILogFormatter):
    """Standard log formatter with timestamp and level."""
    
    def __init__(self, include_timestamp: bool = True, include_source: bool = True):
        self.include_timestamp = include_timestamp
        self.include_source = include_source
    
    def format(self, entry: LogEntry) -> str:
        """Format log entry with timestamp, level, source, and message."""
        parts = []
        
        if self.include_timestamp:
            parts.append(entry.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        
        parts.append(f"[{entry.level.name}]")
        
        if self.include_source and entry.source:
            parts.append(f"({entry.source})")
        
        parts.append(entry.message)
        
        return " ".join(parts)


class CompactFormatter(ILogFormatter):
    """Compact formatter for UI display."""
    
    def format(self, entry: LogEntry) -> str:
        """Format log entry compactly for UI."""
        timestamp = entry.timestamp.strftime('%H:%M:%S')
        return f"{timestamp} [{entry.level.name}] {entry.message}"


class JSONFormatter(ILogFormatter):
    """JSON formatter for structured logging."""
    
    def format(self, entry: LogEntry) -> str:
        """Format log entry as JSON."""
        import json
        data = {
            'timestamp': entry.timestamp.isoformat(),
            'level': entry.level.name,
            'message': entry.message,
            'source': entry.source,
            'context': entry.context
        }
        return json.dumps(data)


class LevelFilter(ILogFilter):
    """Filter log entries by minimum level."""
    
    def __init__(self, min_level: LogLevel):
        self.min_level = min_level
    
    def should_log(self, entry: LogEntry) -> bool:
        """Check if entry meets minimum level."""
        return entry.level.value >= self.min_level.value


class SourceFilter(ILogFilter):
    """Filter log entries by source pattern."""
    
    def __init__(self, allowed_sources: List[str]):
        self.allowed_sources = allowed_sources
    
    def should_log(self, entry: LogEntry) -> bool:
        """Check if entry source is allowed."""
        if not entry.source:
            return True
        return any(pattern in entry.source for pattern in self.allowed_sources)


class ConsoleLogSink(ILogSink):
    """Log sink that writes to console/stdout."""
    
    def __init__(
        self, 
        formatter: ILogFormatter,
        stream=sys.stdout,
        use_colors: bool = True
    ):
        self.formatter = formatter
        self.stream = stream
        self.use_colors = use_colors
    
    def write(self, entry: LogEntry) -> None:
        """Write log entry to console."""
        formatted = self.formatter.format(entry)
        
        if self.use_colors:
            color_code = self._get_color_code(entry.level)
            formatted = f"{color_code}{formatted}\033[0m"
        
        print(formatted, file=self.stream, flush=True)
    
    def flush(self) -> None:
        """Flush the stream."""
        self.stream.flush()
    
    def close(self) -> None:
        """No cleanup needed for console."""
        pass
    
    def _get_color_code(self, level: LogLevel) -> str:
        """Get ANSI color code for log level."""
        colors = {
            LogLevel.DEBUG: '\033[90m',     # Gray
            LogLevel.INFO: '\033[97m',      # White
            LogLevel.WARNING: '\033[93m',   # Yellow
            LogLevel.ERROR: '\033[91m',     # Red
            LogLevel.CRITICAL: '\033[95m',  # Magenta
        }
        return colors.get(level, '\033[97m')


class FileLogSink(ILogSink):
    """Log sink that writes to a file."""
    
    def __init__(
        self,
        file_path: Path,
        formatter: ILogFormatter,
        max_bytes: Optional[int] = None,
        backup_count: int = 5
    ):
        self.file_path = file_path
        self.formatter = formatter
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._file = None
        self._bytes_written = 0
        self._open_file()
    
    def _open_file(self) -> None:
        """Open the log file."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.file_path, 'a', encoding='utf-8')
    
    def write(self, entry: LogEntry) -> None:
        """Write log entry to file."""
        if not self._file:
            self._open_file()
        
        formatted = self.formatter.format(entry)
        line = formatted + '\n'
        
        self._file.write(line)
        self._bytes_written += len(line.encode('utf-8'))
        
        if self.max_bytes and self._bytes_written >= self.max_bytes:
            self._rotate_file()
    
    def flush(self) -> None:
        """Flush the file buffer."""
        if self._file:
            self._file.flush()
    
    def close(self) -> None:
        """Close the file."""
        if self._file:
            self._file.close()
            self._file = None
    
    def _rotate_file(self) -> None:
        """Rotate log files."""
        self.close()
        
        # Rotate existing backup files
        for i in range(self.backup_count - 1, 0, -1):
            source = self.file_path.with_suffix(f'.{i}')
            dest = self.file_path.with_suffix(f'.{i + 1}')
            if source.exists():
                source.rename(dest)
        
        # Move current log to .1
        if self.file_path.exists():
            self.file_path.rename(self.file_path.with_suffix('.1'))
        
        self._bytes_written = 0
        self._open_file()


class UILogSink(ILogSink):
    """Log sink for Qt UI components."""
    
    def __init__(
        self,
        formatter: ILogFormatter,
        text_widget_getter: Callable[[], Any],
        color_enabled: bool = True
    ):
        self.formatter = formatter
        self.text_widget_getter = text_widget_getter
        self.color_enabled = color_enabled
    
    def write(self, entry: LogEntry) -> None:
        """Write log entry to UI widget."""
        widget = self.text_widget_getter()
        if not widget:
            return
        
        formatted = self.formatter.format(entry)
        
        if self.color_enabled and hasattr(widget, 'setTextColor'):
            # For QTextEdit with color support
            color = entry.level.to_color()
            # This would need Qt color conversion in actual implementation
            widget.append(formatted)
        else:
            # For simple text widgets
            widget.append(formatted)
    
    def flush(self) -> None:
        """No buffering in UI sink."""
        pass
    
    def close(self) -> None:
        """No cleanup needed for UI sink."""
        pass


class PrefixedLogSink(ILogSink):
    """Decorator that adds a prefix to all log messages."""
    
    def __init__(self, wrapped: ILogSink, prefix: str):
        self.wrapped = wrapped
        self.prefix = prefix
    
    def write(self, entry: LogEntry) -> None:
        """Write log entry with prefix."""
        prefixed_entry = LogEntry(
            message=f"{self.prefix}{entry.message}",
            level=entry.level,
            timestamp=entry.timestamp,
            context=entry.context,
            source=entry.source
        )
        self.wrapped.write(prefixed_entry)
    
    def flush(self) -> None:
        """Flush wrapped sink."""
        self.wrapped.flush()
    
    def close(self) -> None:
        """Close wrapped sink."""
        self.wrapped.close()


# ============================================================================
# APPLICATION LAYER - Orchestration and business logic
# ============================================================================

class LoggingService:
    """
    Central logging service that coordinates sinks, formatters, and filters.
    
    This is the main entry point for application logging.
    """
    
    def __init__(self, source_name: Optional[str] = None):
        self.source_name = source_name
        self.sinks: List[ILogSink] = []
        self.filters: List[ILogFilter] = []
        self.context: Dict[str, Any] = {}
    
    def add_sink(self, sink: ILogSink) -> None:
        """Add a log sink."""
        self.sinks.append(sink)
    
    def remove_sink(self, sink: ILogSink) -> None:
        """Remove a log sink."""
        if sink in self.sinks:
            self.sinks.remove(sink)
    
    def add_filter(self, filter: ILogFilter) -> None:
        """Add a log filter."""
        self.filters.append(filter)
    
    def set_context(self, **kwargs) -> None:
        """Set context that will be included in all log entries."""
        self.context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context."""
        self.context.clear()
    
    def log(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        **extra_context
    ) -> None:
        """Log a message at the specified level."""
        entry = LogEntry(
            message=message,
            level=level,
            timestamp=datetime.now(),
            context={**self.context, **extra_context},
            source=self.source_name
        )
        
        # Apply filters
        for filter in self.filters:
            if not filter.should_log(entry):
                return
        
        # Write to all sinks
        for sink in self.sinks:
            try:
                sink.write(entry)
            except Exception as e:
                # Fallback to stderr if sink fails
                print(f"Logging sink failed: {e}", file=sys.stderr)
    
    def debug(self, message: str, **context) -> None:
        """Log debug message."""
        self.log(message, LogLevel.DEBUG, **context)
    
    def info(self, message: str, **context) -> None:
        """Log info message."""
        self.log(message, LogLevel.INFO, **context)
    
    def warning(self, message: str, **context) -> None:
        """Log warning message."""
        self.log(message, LogLevel.WARNING, **context)
    
    def error(self, message: str, **context) -> None:
        """Log error message."""
        self.log(message, LogLevel.ERROR, **context)
    
    def critical(self, message: str, **context) -> None:
        """Log critical message."""
        self.log(message, LogLevel.CRITICAL, **context)
    
    def flush_all(self) -> None:
        """Flush all sinks."""
        for sink in self.sinks:
            try:
                sink.flush()
            except Exception:
                pass
    
    def close_all(self) -> None:
        """Close all sinks."""
        for sink in self.sinks:
            try:
                sink.close()
            except Exception:
                pass
    
    @contextmanager
    def scoped_context(self, **kwargs):
        """Context manager for temporary context."""
        old_context = self.context.copy()
        self.context.update(kwargs)
        try:
            yield self
        finally:
            self.context = old_context


class LoggingServiceFactory:
    """Factory for creating pre-configured logging services."""
    
    @staticmethod
    def create_console_logger(
        source_name: str,
        min_level: LogLevel = LogLevel.INFO
    ) -> LoggingService:
        """Create a logger that writes to console."""
        service = LoggingService(source_name)
        
        formatter = CompactFormatter()
        sink = ConsoleLogSink(formatter)
        service.add_sink(sink)
        
        filter = LevelFilter(min_level)
        service.add_filter(filter)
        
        return service
    
    @staticmethod
    def create_file_logger(
        source_name: str,
        log_file: Path,
        min_level: LogLevel = LogLevel.DEBUG,
        max_bytes: Optional[int] = 10 * 1024 * 1024  # 10MB
    ) -> LoggingService:
        """Create a logger that writes to a file."""
        service = LoggingService(source_name)
        
        formatter = StandardFormatter()
        sink = FileLogSink(log_file, formatter, max_bytes=max_bytes)
        service.add_sink(sink)
        
        filter = LevelFilter(min_level)
        service.add_filter(filter)
        
        return service
    
    @staticmethod
    def create_multi_logger(
        source_name: str,
        console_level: LogLevel = LogLevel.INFO,
        file_path: Optional[Path] = None,
        file_level: LogLevel = LogLevel.DEBUG
    ) -> LoggingService:
        """Create a logger that writes to both console and file."""
        service = LoggingService(source_name)
        
        # Console sink
        console_formatter = CompactFormatter()
        console_sink = ConsoleLogSink(console_formatter)
        service.add_sink(console_sink)
        
        # File sink (if path provided)
        if file_path:
            file_formatter = StandardFormatter()
            file_sink = FileLogSink(file_path, file_formatter)
            service.add_sink(file_sink)
        
        # Filters - apply minimum of console and file levels
        min_level = min(console_level, file_level if file_path else console_level)
        filter = LevelFilter(min_level)
        service.add_filter(filter)
        
        return service


class LoggingContext:
    """
    Global logging context for managing application-wide logging.
    
    This provides a singleton-like pattern for accessing logging services.
    """
    
    _instance: Optional['LoggingContext'] = None
    
    def __init__(self):
        self._services: Dict[str, LoggingService] = {}
        self._default_service: Optional[LoggingService] = None
    
    @classmethod
    def get_instance(cls) -> 'LoggingContext':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_service(self, name: str, service: LoggingService) -> None:
        """Register a named logging service."""
        self._services[name] = service
    
    def get_service(self, name: str) -> Optional[LoggingService]:
        """Get a named logging service."""
        return self._services.get(name)
    
    def set_default_service(self, service: LoggingService) -> None:
        """Set the default logging service."""
        self._default_service = service
    
    def get_default_service(self) -> Optional[LoggingService]:
        """Get the default logging service."""
        return self._default_service
    
    def shutdown(self) -> None:
        """Shutdown all logging services."""
        for service in self._services.values():
            service.flush_all()
            service.close_all()
        
        if self._default_service:
            self._default_service.flush_all()
            self._default_service.close_all()


class BridgeHandler(logging.Handler):
    """Bridge from standard logging to new infrastructure."""
    def __init__(self, service: LoggingService):
        super().__init__()
        self.service = service
        
    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            
            level_map = {
                logging.DEBUG: LogLevel.DEBUG,
                logging.INFO: LogLevel.INFO,
                logging.WARNING: LogLevel.WARNING,
                logging.ERROR: LogLevel.ERROR,
                logging.CRITICAL: LogLevel.CRITICAL
            }
            level = level_map.get(record.levelno, LogLevel.INFO)
            
            # Use logger name as source
            self.service.log(msg, level=level, source=record.name)
        except Exception:
            self.handleError(record)


def setup_logging_bridge(service: LoggingService, level: str = "INFO") -> None:
    """Setup a bridge to forward standard logging to the provided service."""
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
    
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric_level)
    
    handler = BridgeHandler(service)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    
    root.addHandler(handler)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_logger(name: str) -> LoggingService:
    """Get or create a logger with the given name."""
    context = LoggingContext.get_instance()
    service = context.get_service(name)
    
    if service is None:
        # Create a default console logger
        service = LoggingServiceFactory.create_console_logger(name)
        context.register_service(name, service)
    
    return service


def configure_default_logging(
    console_level: LogLevel = LogLevel.INFO,
    log_file: Optional[Path] = None,
    file_level: LogLevel = LogLevel.DEBUG
) -> LoggingService:
    """Configure default application logging."""
    service = LoggingServiceFactory.create_multi_logger(
        "default",
        console_level=console_level,
        file_path=log_file,
        file_level=file_level
    )
    
    context = LoggingContext.get_instance()
    context.set_default_service(service)
    context.register_service("default", service)
    
    return service
