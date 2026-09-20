"""CrawlerLogHandler must carry each record's level to the UI event."""

import logging

from mobile_crawler.domain.crawler_agent_service import CrawlerLogHandler


def test_emit_forwards_record_level(tmp_path):
    calls = []
    handler = CrawlerLogHandler(7, str(tmp_path / "trace.jsonl"), lambda *a: calls.append(a), True)

    for level in (logging.DEBUG, logging.WARNING, logging.ERROR):
        handler.emit(logging.LogRecord("crawler_agent", level, __file__, 1, "msg", None, None))

    assert [c[4] for c in calls] == ["DEBUG", "WARNING", "ERROR"]
    assert calls[0][:4] == ("on_debug_log", 7, 0, "msg")
