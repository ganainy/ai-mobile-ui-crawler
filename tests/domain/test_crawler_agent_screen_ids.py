"""CrawlerAgentService gives step_logs rows screen ids and emits on_screen_processed.

The screen of a decision's screenshot is each tool's from_screen_id; the screen of the
next screenshot becomes their to_screen_id. Runs against a real SQLite database.
"""

import asyncio
import io
import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from mobile_crawler.domain.crawler_agent.agent.common.events import ToolExecutionEvent
from mobile_crawler.domain.crawler_agent.agent.manager.events import ManagerResponseEvent
from mobile_crawler.domain.crawler_agent_service import CrawlerAgentService
from mobile_crawler.infrastructure.analysis_bundle import AnalysisBundleWriter
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository


@pytest.fixture
def db(tmp_path):
    manager = DatabaseManager(tmp_path / "crawler.db")
    manager.migrate_schema()
    return manager


@pytest.fixture
def run_id(db, tmp_path):
    session = tmp_path / "session"
    session.mkdir()
    return RunRepository(db).create_run(
        Run(
            id=None,
            device_id="emulator-5554",
            app_package="com.example.health",
            start_activity=None,
            start_time=datetime(2026, 9, 23, 10, 0, 0),
            end_time=None,
            status="RUNNING",
            ai_provider="gemini",
            ai_model="gemini-x",
            total_steps=0,
            unique_screens=0,
            session_path=str(session),
        )
    )


@pytest.fixture
def emitted():
    return []


@pytest.fixture
def service(db, run_id, tmp_path, emitted):
    config = Mock()
    config.get.side_effect = lambda key, default=None: default
    with patch("mobile_crawler.domain.crawler_agent_service.OMNIPARSER_AVAILABLE", False):
        svc = CrawlerAgentService(config_manager=config, ai_interaction_repository=None, device_id="dev")
    with patch("mobile_crawler.infrastructure.database.DatabaseManager", return_value=db):
        svc.begin_step_tracking(
            run_id=run_id,
            emit_step_phase_event=lambda name, *args: emitted.append((name, args)),
            screenshots_dir=str(tmp_path / "session" / "screenshots"),
        )
    svc._ui_dump_validator = None
    return svc


def _screen(reverse: bool) -> bytes:
    """A horizontal gradient; the reversed one has the opposite dHash (a different screen)."""
    image = Image.new("L", (90, 160))
    image.putdata([(255 - x if reverse else x) * 2 for _ in range(160) for x in range(90)])
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


SCREEN_A = _screen(reverse=False)
SCREEN_B = _screen(reverse=True)


def _dispatch(service, *events):
    async def go():
        for event in events:
            await service._dispatch_workflow_event(event)

    asyncio.run(go())


def _tool(name):
    return ToolExecutionEvent(tool_name=name, tool_args={}, success=True, summary="done", duration_ms=10.0)


def _walk(service):
    """Screen A: two tools, screen B: one tool, back to screen A: one tool."""
    _dispatch(
        service,
        ManagerResponseEvent(response="plan", screenshot=SCREEN_A),
        _tool("type"),
        _tool("type"),
        ManagerResponseEvent(response="plan", screenshot=SCREEN_B),
        _tool("click"),
        ManagerResponseEvent(response="plan", screenshot=SCREEN_A),
        _tool("swipe"),
    )


def test_step_logs_get_from_and_to_screen_ids(service, db, run_id):
    _walk(service)

    rows = StepLogRepository(db).get_step_logs_by_run(run_id)

    a, b = rows[0].from_screen_id, rows[2].from_screen_id
    assert a is not None and b is not None and a != b
    assert [(r.from_screen_id, r.to_screen_id) for r in rows] == [(a, b), (a, b), (b, a), (a, None)]
    assert service.unique_screen_count == 2


def test_screen_processed_events_report_new_and_revisited_screens(service, run_id, emitted):
    _walk(service)

    screens = [args for name, args in emitted if name == "on_screen_processed"]

    # (run_id, step_number, screen_id, is_new, visit_count, total_screens)
    assert [(s[0], s[1], s[3], s[4], s[5]) for s in screens] == [
        (run_id, 1, True, 1, 1),
        (run_id, 2, True, 1, 2),
        (run_id, 3, False, 2, 2),
    ]
    assert screens[0][2] == screens[2][2]


def test_analysis_bundle_counts_the_start_screen(service, db, run_id, tmp_path):
    _dispatch(
        service,
        ManagerResponseEvent(response="plan", screenshot=SCREEN_A),
        _tool("click"),
        ManagerResponseEvent(response="plan", screenshot=SCREEN_B),
    )

    out = AnalysisBundleWriter(db).write(run_id, tmp_path / "analysis")

    run = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert run["statistics"]["unique_screens_visited"] == 2


def test_unreadable_screenshot_leaves_screen_ids_empty(service, db, run_id):
    _dispatch(service, ManagerResponseEvent(response="plan", screenshot=b"not an image"), _tool("click"))

    (row,) = StepLogRepository(db).get_step_logs_by_run(run_id)
    assert (row.from_screen_id, row.to_screen_id) == (None, None)
    assert service.unique_screen_count == 0
