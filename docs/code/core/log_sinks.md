---
generated: true
file: src/mobile_crawler/core/log_sinks.py
---
# mobile_crawler.core.log_sinks

Log sinks for multi-sink logging architecture.

Source: `src/mobile_crawler/core/log_sinks.py`

## Classes
- `LogLevel`
- `LogSink`
- `ConsoleSink`
- `JSONEventSink`
- `FileSink`
- `DatabaseSink`
- `QLogHandler`
- `_LineCapturingStream`

## Functions
- `capture_stdout_to_ui`

## Imports
- [[code/config/_index|config]]
- [[code/infrastructure/database|infrastructure.database]]

## Imported by
- [[code/core/crawler_loop|core.crawler_loop]]
- [[code/core/logging_service|core.logging_service]]
- [[code/ui/main_window|ui.main_window]]
