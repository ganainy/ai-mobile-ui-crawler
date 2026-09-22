"""CrawlerAgentService writes one step_logs row per executed tool (issue #24).

Events go through the service's own workflow-event dispatch against a real
SQLite database, so these tests fail if the crawler stops writing step logs.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from mobile_crawler.domain.crawler_agent.agent.common.events import ToolExecutionEvent
from mobile_crawler.domain.crawler_agent.agent.executor.events import ExecutorResponseEvent
from mobile_crawler.domain.crawler_agent.agent.fast_agent.events import FastAgentResponseEvent
from mobile_crawler.domain.crawler_agent_service import CrawlerAgentService
from mobile_crawler.infrastructure.analysis_bundle import AnalysisBundleWriter
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository
from mobile_crawler.infrastructure.step_phase_repository import StepPhaseRepository


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
            end_time=datetime(2026, 9, 23, 10, 5, 0),
            status="STOPPED",
            ai_provider="gemini",
            ai_model="gemini-x",
            total_steps=0,
            unique_screens=0,
            session_path=str(session),
        )
    )


@pytest.fixture
def service(db, run_id):
    config = Mock()
    config.get.side_effect = lambda key, default=None: default
    with patch("mobile_crawler.domain.crawler_agent_service.OMNIPARSER_AVAILABLE", False):
        svc = CrawlerAgentService(config_manager=config, ai_interaction_repository=None, device_id="dev")
    with patch("mobile_crawler.infrastructure.database.DatabaseManager", return_value=db):
        svc.begin_step_tracking(run_id=run_id)
    svc._ui_dump_validator = None
    return svc


def _dispatch(service, *events):
    async def go():
        for event in events:
            await service._dispatch_workflow_event(event)

    asyncio.run(go())


def _executor_response(thought, description, llm_ms):
    return ExecutorResponseEvent(
        response=f"### Thought\n{thought}\n### Action\n{{}}\n### Description\n{description}",
        executor_llm_ms=llm_ms,
        parsed_action={"thought": thought, "action": "{}", "description": description},
    )


def _tool(name, success=True, summary="done", duration_ms=50.0, **args):
    return ToolExecutionEvent(tool_name=name, tool_args=args, success=success, summary=summary, duration_ms=duration_ms)


def test_each_tool_execution_writes_a_step_log_row(service, db, run_id):
    _dispatch(
        service,
        _executor_response("Fill in the login form", "Type the email then submit", 900.0),
        _tool("type", summary="Typed into field 3", duration_ms=120.0, text="a@b.com", index=3),
        _tool("click", success=False, summary="Element 7 not found", duration_ms=40.0, index=7),
    )

    rows = StepLogRepository(db).get_step_logs_by_run(run_id)

    assert [r.step_number for r in rows] == [1, 2]
    first, second = rows
    assert first.action_type == "type"
    assert first.action_description == "Typed into field 3"
    assert first.input_text == "a@b.com"
    assert first.execution_success is True
    assert first.error_message is None
    assert first.action_duration_ms == 120.0
    assert first.ai_response_time_ms == 900.0
    assert first.ai_reasoning == "Fill in the login form"

    assert second.action_type == "click"
    assert second.execution_success is False
    assert second.error_message == "Element 7 not found"
    assert second.input_text is None
    # Same Executor decision (an Action Batch): reasoning carries over, the LLM time is counted once.
    assert second.ai_reasoning == "Fill in the login form"
    assert second.ai_response_time_ms is None


def test_step_log_numbers_match_phase_transition_numbers(service, db, run_id):
    _dispatch(service, _executor_response("t", "d", 10.0), _tool("click"), _tool("swipe"))

    log_numbers = {r.step_number for r in StepLogRepository(db).get_step_logs_by_run(run_id)}
    phase_numbers = {t.step_number for t in StepPhaseRepository(db).get_transitions_for_run(run_id)}

    assert log_numbers == {1, 2}
    assert phase_numbers == log_numbers


def test_fast_agent_thought_becomes_reasoning(service, db, run_id):
    _dispatch(
        service,
        FastAgentResponseEvent(thought="Open settings", fast_agent_llm_ms=300.0),
        _tool("click"),
    )

    (row,) = StepLogRepository(db).get_step_logs_by_run(run_id)
    assert row.ai_reasoning == "Open settings"
    assert row.ai_response_time_ms == 300.0


def test_analysis_bundle_joins_step_logs_with_timing(service, db, run_id, tmp_path):
    _dispatch(
        service,
        _executor_response("Go on", "Tap next", 500.0),
        _tool("click", summary="Tapped Next"),
        _tool("click", success=False, summary="Element 9 not found"),
    )

    out = AnalysisBundleWriter(db).write(run_id, tmp_path / "analysis")

    lines = [json.loads(line) for line in (out / "steps.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [line["step_number"] for line in lines] == [1, 2]
    assert lines[0]["action_type"] == "click"
    assert lines[0]["execution_success"] is True
    assert lines[0]["timing"] is not None
    assert lines[1]["error_message"] == "Element 9 not found"

    run = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert len(run["step_logs"]) == 2
    assert run["statistics"]["successful_actions"] == 1
    assert run["statistics"]["failed_actions"] == 1


def test_screenshots_land_on_the_steps_their_decision_ran(db, run_id, tmp_path):
    """AI-call numbering differs from step numbering once a decision runs several tools."""
    from mobile_crawler.domain.crawler_agent.agent.manager.events import ManagerResponseEvent
    from mobile_crawler.infrastructure.ai_interaction_repository import AIInteractionRepository

    config = Mock()
    config.get.side_effect = lambda key, default=None: default
    with patch("mobile_crawler.domain.crawler_agent_service.OMNIPARSER_AVAILABLE", False):
        svc = CrawlerAgentService(config, AIInteractionRepository(db), device_id="dev")
    shots = tmp_path / "session" / "screenshots"
    with patch("mobile_crawler.infrastructure.database.DatabaseManager", return_value=db):
        svc.begin_step_tracking(run_id=run_id, screenshots_dir=str(shots))
    svc._ui_dump_validator = None

    _dispatch(
        svc,
        ManagerResponseEvent(response="plan", screenshot=b"first"),
        _executor_response("fill", "type both", 10.0),
        _tool("type", text="a"),
        _tool("type", text="b"),
        ManagerResponseEvent(response="plan", screenshot=b"second"),
        _executor_response("go", "submit", 10.0),
        _tool("click"),
    )

    out = AnalysisBundleWriter(db).write(run_id, tmp_path / "analysis")

    lines = [json.loads(line) for line in (out / "steps.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [line["screenshot"] for line in lines] == [
        "screenshots/step_0001.png",
        None,
        "screenshots/step_0002.png",
    ]
