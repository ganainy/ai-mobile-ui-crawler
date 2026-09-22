"""ReportGenerator.generate also writes the AI-readable Analysis Bundle."""

import json
from datetime import datetime

import pytest

from mobile_crawler.domain.report_generator import ReportGenerator
from mobile_crawler.infrastructure.ai_interaction_repository import (
    AIInteraction,
    AIInteractionRepository,
)
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository
from mobile_crawler.infrastructure.step_log_repository import StepLog, StepLogRepository


@pytest.fixture
def seeded_run(tmp_path):
    """A finished run with two steps and one AI interaction, in a session folder."""
    session = tmp_path / "run_1_session"
    for sub in ("screenshots", "reports", "data"):
        (session / sub).mkdir(parents=True)

    db = DatabaseManager(tmp_path / "crawler.db")
    db.migrate_schema()

    run_id = RunRepository(db).create_run(
        Run(
            id=None,
            device_id="emulator-5554",
            app_package="com.example.health",
            start_activity=None,
            start_time=datetime(2026, 9, 19, 10, 0, 0),
            end_time=datetime(2026, 9, 19, 10, 5, 0),
            status="STOPPED",
            ai_provider="gemini",
            ai_model="gemini-x",
            total_steps=2,
            unique_screens=0,
            session_path=str(session),
            stop_reason="step_limit",
        )
    )

    steps = StepLogRepository(db)
    steps.create_step_log(
        StepLog(
            id=None,
            run_id=run_id,
            step_number=1,
            timestamp=datetime(2026, 9, 19, 10, 1, 0),
            from_screen_id=None,
            to_screen_id=None,
            action_type="click",
            action_description="Tap Sign in",
            target_bbox_json=None,
            input_text=None,
            execution_success=True,
            error_message=None,
            action_duration_ms=120.0,
            ai_response_time_ms=900.0,
            ai_reasoning="Login is the obvious entry point",
        )
    )
    steps.create_step_log(
        StepLog(
            id=None,
            run_id=run_id,
            step_number=2,
            timestamp=datetime(2026, 9, 19, 10, 2, 0),
            from_screen_id=None,
            to_screen_id=None,
            action_type="scroll_down",
            action_description="Scroll feed",
            target_bbox_json=None,
            input_text=None,
            execution_success=False,
            error_message="element not found",
            action_duration_ms=80.0,
            ai_response_time_ms=700.0,
            ai_reasoning="Look for more content",
        )
    )

    shot = session / "screenshots" / "step_1.png"
    shot.write_bytes(b"png")
    AIInteractionRepository(db).create_ai_interaction(
        AIInteraction(
            id=None,
            run_id=run_id,
            step_number=1,
            timestamp=datetime(2026, 9, 19, 10, 1, 0),
            request_json=json.dumps({"user_prompt": "PROMPT-BODY-SHOULD-NOT-LEAK"}),
            screenshot_path=str(shot),
            response_raw="raw",
            response_parsed_json="{}",
            tokens_input=100,
            tokens_output=20,
            latency_ms=900.0,
            success=True,
            error_message=None,
            retry_count=0,
        )
    )
    return db, run_id, session


def test_generate_writes_analysis_bundle_next_to_html(seeded_run):
    db, run_id, session = seeded_run

    html_path = ReportGenerator(db).generate(run_id)

    assert html_path.endswith(f"report_run_{run_id}.html")
    analysis = session / "analysis"
    assert (analysis / "analysis.md").is_file()
    assert (analysis / "steps.jsonl").is_file()
    assert (analysis / "run.json").is_file()


def test_steps_jsonl_has_one_line_per_step_with_relative_screenshot(seeded_run):
    db, run_id, session = seeded_run
    ReportGenerator(db).generate(run_id)

    lines = (session / "analysis" / "steps.jsonl").read_text(encoding="utf-8").splitlines()
    steps = [json.loads(line) for line in lines]

    assert [s["step_number"] for s in steps] == [1, 2]
    assert steps[0]["action_type"] == "click"
    assert steps[0]["ai_reasoning"] == "Login is the obvious entry point"
    assert steps[0]["screenshot"] == "screenshots/step_1.png"
    assert steps[1]["execution_success"] is False
    assert steps[1]["error_message"] == "element not found"
    assert steps[1]["screenshot"] is None
    assert "PROMPT-BODY-SHOULD-NOT-LEAK" not in json.dumps(steps)


def test_analysis_md_summarises_run_and_stop_reason(seeded_run):
    db, run_id, session = seeded_run
    ReportGenerator(db).generate(run_id)

    text = (session / "analysis" / "analysis.md").read_text(encoding="utf-8")

    assert "com.example.health" in text
    assert "gemini-x" in text
    assert "step_limit" in text
    assert "1 of 2" in text  # one failed step of two, as "successful steps"


def test_run_json_keeps_full_prompts(seeded_run):
    db, run_id, session = seeded_run
    ReportGenerator(db).generate(run_id)

    data = json.loads((session / "analysis" / "run.json").read_text(encoding="utf-8"))

    assert data["run"]["stop_reason"] == "step_limit"
    assert len(data["step_logs"]) == 2
    assert "PROMPT-BODY-SHOULD-NOT-LEAK" in json.dumps(data["ai_interactions"])


@pytest.fixture
def problem_run(tmp_path):
    """A run with a repeated failing action, AI errors and a config snapshot."""
    session = tmp_path / "run_2_session"
    for sub in ("screenshots", "reports", "data"):
        (session / sub).mkdir(parents=True)
    (session / "data" / "config_snapshot.json").write_text(
        json.dumps({"ai_model": "gemini-x", "max_steps": 40, "git_commit": "abc1234"}),
        encoding="utf-8",
    )

    db = DatabaseManager(tmp_path / "crawler.db")
    db.migrate_schema()
    run_id = RunRepository(db).create_run(
        Run(
            id=None,
            device_id="d",
            app_package="com.example.health",
            start_activity=None,
            start_time=datetime(2026, 9, 19, 10, 0, 0),
            end_time=datetime(2026, 9, 19, 10, 5, 0),
            status="COMPLETED",
            ai_provider="gemini",
            ai_model="gemini-x",
            total_steps=5,
            unique_screens=0,
            session_path=str(session),
            stop_reason="duration_limit",
            guided_progress_json=json.dumps(
                {
                    "scenarios": ["Open settings", "Log a meal"],
                    "final_plan": "1. Log a meal",
                    "last_subgoal": "Log a meal",
                }
            ),
        )
    )
    steps = StepLogRepository(db)
    for n in range(1, 6):
        steps.create_step_log(
            StepLog(
                id=None,
                run_id=run_id,
                step_number=n,
                timestamp=datetime(2026, 9, 19, 10, n, 0),
                from_screen_id=None,
                to_screen_id=None,
                action_type="click",
                action_description="Tap Continue",
                target_bbox_json=None,
                input_text=None,
                execution_success=(n == 1),
                error_message=None if n == 1 else "no effect",
                action_duration_ms=50.0,
                ai_response_time_ms=100.0 * n,
                ai_reasoning="try again",
            )
        )
    ai = AIInteractionRepository(db)
    for n, ok in ((1, True), (2, False)):
        ai.create_ai_interaction(
            AIInteraction(
                id=None,
                run_id=run_id,
                step_number=n,
                timestamp=datetime(2026, 9, 19, 10, n, 0),
                request_json="{}",
                screenshot_path=None,
                response_raw="r",
                response_parsed_json=None,
                tokens_input=1000,
                tokens_output=50,
                latency_ms=800.0,
                success=ok,
                error_message=None if ok else "429 rate limited",
                retry_count=0,
            )
        )
    return db, run_id, session


def _analysis_md(problem_run) -> str:
    db, run_id, session = problem_run
    ReportGenerator(db).generate(run_id)
    return (session / "analysis" / "analysis.md").read_text(encoding="utf-8")


def test_analysis_flags_a_repeated_action(problem_run):
    text = _analysis_md(problem_run)

    assert "## Repeated actions" in text
    assert "Tap Continue" in text
    assert "5 times" in text


def test_analysis_lists_failed_steps_with_errors(problem_run):
    text = _analysis_md(problem_run)

    assert "## Failed steps" in text
    assert "step 2" in text
    assert "no effect" in text


def test_analysis_reports_tokens_and_ai_errors(problem_run):
    text = _analysis_md(problem_run)

    assert "## AI usage" in text
    assert "2000 input" in text
    assert "100 output" in text
    assert "429 rate limited" in text


def test_analysis_shows_guided_scenarios_and_remaining_plan(problem_run):
    text = _analysis_md(problem_run)

    assert "## Guided scenarios" in text
    assert "Open settings" in text
    assert "Log a meal" in text
    assert "Last plan" in text


def test_analysis_and_run_json_carry_the_config_snapshot(problem_run):
    db, run_id, session = problem_run
    text = _analysis_md(problem_run)
    data = json.loads((session / "analysis" / "run.json").read_text(encoding="utf-8"))

    assert "## Config" in text
    assert "abc1234" in text
    assert data["config"]["max_steps"] == 40


def test_analysis_without_snapshot_says_so(seeded_run):
    db, run_id, session = seeded_run
    ReportGenerator(db).generate(run_id)

    text = (session / "analysis" / "analysis.md").read_text(encoding="utf-8")
    data = json.loads((session / "analysis" / "run.json").read_text(encoding="utf-8"))

    assert "No config snapshot" in text
    assert data["config"] is None


def test_html_report_contains_the_same_analysis_sections(problem_run):
    db, run_id, session = problem_run

    html_path = ReportGenerator(db).generate(run_id)
    html = open(html_path, encoding="utf-8").read()

    for heading in ("Repeated actions", "Failed steps", "AI usage", "Guided scenarios", "Config"):
        assert f"<h2>{heading}</h2>" in html
    assert "Tap Continue" in html
    assert "429 rate limited" in html
    assert "duration_limit" in html  # stop reason shown in the summary


def test_html_report_escapes_app_text(problem_run):
    db, run_id, session = problem_run
    # A hostile action description must not inject markup into the HTML report.
    from mobile_crawler.infrastructure.step_log_repository import StepLog, StepLogRepository

    StepLogRepository(db).create_step_log(
        StepLog(
            id=None,
            run_id=run_id,
            step_number=6,
            timestamp=datetime(2026, 9, 19, 10, 6, 0),
            from_screen_id=None,
            to_screen_id=None,
            action_type="click",
            action_description="<script>alert(1)</script>",
            target_bbox_json=None,
            input_text=None,
            execution_success=False,
            error_message="<b>boom</b>",
            action_duration_ms=1.0,
            ai_response_time_ms=1.0,
            ai_reasoning=None,
        )
    )

    html = open(ReportGenerator(db).generate(run_id), encoding="utf-8").read()

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


# -- telemetry -----------------------------------------------------------------

from mobile_crawler.infrastructure.telemetry_client import TelemetrySummary  # noqa: E402


class FakeTelemetryClient:
    provider = "langfuse"

    def __init__(self, summary=None, error=None):
        self.summary = summary
        self.error = error
        self.fetched = []

    def fetch(self, session_id):
        self.fetched.append(session_id)
        if self.error:
            raise self.error
        return self.summary


@pytest.fixture
def traced_run(problem_run):
    """problem_run, recorded as a Langfuse-traced run with a trace session id."""
    db, run_id, session = problem_run
    (session / "data" / "config_snapshot.json").write_text(
        json.dumps({"enable_tracing": True, "tracing_provider": "langfuse"}), encoding="utf-8"
    )
    RunRepository(db).update_trace_id(run_id, "run-2-abcd1234")
    return db, run_id, session


def _run_json(session):
    return json.loads((session / "analysis" / "run.json").read_text(encoding="utf-8"))


def test_auto_generate_marks_telemetry_pending_without_calling_the_server(traced_run):
    db, run_id, session = traced_run
    client = FakeTelemetryClient(summary=TelemetrySummary(status="ok"))

    html = open(
        ReportGenerator(db, telemetry_client_factory=lambda provider: client).generate(run_id), encoding="utf-8"
    ).read()

    assert client.fetched == []
    assert _run_json(session)["telemetry"]["status"] == "pending"
    assert "<h2>Telemetry</h2>" in html
    assert "pending" in (session / "analysis" / "analysis.md").read_text(encoding="utf-8")


def test_manual_generate_fetches_telemetry_into_the_report(traced_run):
    db, run_id, session = traced_run
    client = FakeTelemetryClient(
        summary=TelemetrySummary(
            status="ok",
            provider="langfuse",
            trace_count=3,
            total_cost=0.0456,
            avg_latency_ms=1234.0,
            link="https://lf.example/project/p/sessions/run-2-abcd1234",
        )
    )
    requested = []

    def factory(provider):
        requested.append(provider)
        return client

    html = open(
        ReportGenerator(db, telemetry_client_factory=factory).generate(run_id, fetch_telemetry=True),
        encoding="utf-8",
    ).read()

    assert requested == ["langfuse"]  # provider comes from the run's config snapshot
    assert client.fetched == ["run-2-abcd1234"]
    assert _run_json(session)["telemetry"]["total_cost"] == 0.0456
    md = (session / "analysis" / "analysis.md").read_text(encoding="utf-8")
    assert "https://lf.example/project/p/sessions/run-2-abcd1234" in md
    assert "https://lf.example/project/p/sessions/run-2-abcd1234" in html


def test_unreachable_telemetry_server_never_fails_the_report(traced_run):
    db, run_id, session = traced_run
    client = FakeTelemetryClient(error=ConnectionError("connection refused"))

    ReportGenerator(db, telemetry_client_factory=lambda provider: client).generate(run_id, fetch_telemetry=True)

    data = _run_json(session)
    assert data["telemetry"]["status"] == "unreachable"
    assert "connection refused" in data["telemetry"]["note"]
    assert (session / "analysis" / "analysis.md").is_file()


def test_run_without_trace_id_reports_no_trace_id(problem_run):
    db, run_id, session = problem_run

    ReportGenerator(db).generate(run_id, fetch_telemetry=True)

    assert _run_json(session)["telemetry"]["status"] == "no_trace_id"


def test_tracing_disabled_in_snapshot_means_not_configured(problem_run):
    db, run_id, session = problem_run
    RunRepository(db).update_trace_id(run_id, "run-2-abcd1234")  # snapshot has no tracing keys

    ReportGenerator(db, telemetry_client_factory=lambda provider: pytest.fail("no client")).generate(
        run_id, fetch_telemetry=True
    )

    assert _run_json(session)["telemetry"]["status"] == "not_configured"


# -- phase-level timing breakdown ---------------------------------------------

from mobile_crawler.domain.step_phase_models import StepPhaseTransition  # noqa: E402
from mobile_crawler.infrastructure.step_phase_repository import StepPhaseRepository  # noqa: E402


@pytest.fixture
def timed_run(seeded_run):
    """seeded_run with phase transitions for step 1 (sub-phases and one validation retry)."""
    db, run_id, session = seeded_run
    phases = StepPhaseRepository(db)

    def record(from_phase, to_phase, second, duration_ms, metadata=None):
        phases.record_transition(
            StepPhaseTransition(
                id=None,
                run_id=run_id,
                step_number=1,
                from_phase=from_phase,
                to_phase=to_phase,
                timestamp=datetime(2026, 9, 19, 10, 1, second),
                duration_ms=duration_ms,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
        )

    record("capture", "decide", 1, 1500.0, {"sub_phases": {"a11y_ms": 400.0, "omniparser_ms": 900.0}})
    record(
        "decide",
        "act",
        4,
        3000.0,
        {
            "sub_phases": {"manager_llm_ms": 2000.0},
            "validation_retries": [{"reason": "plan missing subgoal", "attempt": 1, "timestamp": "t"}],
        },
    )
    record("act", "checkpoint", 5, 500.0)
    return db, run_id, session


def _steps_jsonl(session):
    lines = (session / "analysis" / "steps.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_steps_jsonl_carries_the_phase_timing_breakdown(timed_run):
    db, run_id, session = timed_run
    ReportGenerator(db).generate(run_id)

    step1, step2 = _steps_jsonl(session)
    timing = step1["timing"]

    assert timing["total_step_duration_ms"] == 5000.0
    assert {"phase": "capture", "metric": "phase total", "duration_ms": 1500.0} in timing["phases"]
    assert {"phase": "capture", "metric": "a11y_ms", "duration_ms": 400.0} in timing["phases"]
    assert {"phase": "decide", "metric": "manager_llm_ms", "duration_ms": 2000.0} in timing["phases"]
    assert timing["validation_retry_count"] == 1
    assert timing["validation_retries"][0]["reason"] == "plan missing subgoal"
    assert step2["timing"] is None  # no phase rows recorded for step 2


def test_run_json_keeps_the_raw_phase_transitions(timed_run):
    db, run_id, session = timed_run
    ReportGenerator(db).generate(run_id)

    transitions = _run_json(session)["step_phase_transitions"]

    assert [t["from_phase"] for t in transitions] == ["capture", "decide", "act"]
    assert transitions[0]["step_number"] == 1
    assert json.loads(transitions[1]["metadata_json"])["sub_phases"]["manager_llm_ms"] == 2000.0


def test_analysis_md_summarises_phase_timings_and_retries(timed_run):
    db, run_id, session = timed_run
    html = open(ReportGenerator(db).generate(run_id), encoding="utf-8").read()
    text = (session / "analysis" / "analysis.md").read_text(encoding="utf-8")

    assert "## Timing breakdown" in text
    assert "capture phase total: avg 1500 ms" in text
    assert "capture a11y_ms: avg 400 ms" in text
    assert "decide manager_llm_ms: avg 2000 ms" in text
    assert "Manager validation retries: 1" in text
    assert "step 1 attempt 1: plan missing subgoal" in text
    assert "<h2>Timing breakdown</h2>" in html


def test_steps_jsonl_has_a_line_for_phase_timed_steps_without_a_step_log(timed_run):
    # Real crawls record phase transitions but no step_logs rows; their timing must still be exported.
    db, run_id, session = timed_run
    StepPhaseRepository(db).record_transition(
        StepPhaseTransition(
            id=None,
            run_id=run_id,
            step_number=3,
            from_phase="capture",
            to_phase="decide",
            timestamp=datetime(2026, 9, 19, 10, 3, 0),
            duration_ms=700.0,
        )
    )
    ReportGenerator(db).generate(run_id)

    steps = _steps_jsonl(session)

    assert [s["step_number"] for s in steps] == [1, 2, 3]
    assert list(steps[2]) == list(steps[0])  # same keys as a step_logs-backed line
    assert steps[2]["action_type"] is None
    assert steps[2]["timing"]["total_step_duration_ms"] == 700.0


def test_malformed_sub_phase_values_are_skipped_not_fatal():
    from mobile_crawler.domain.step_phase_models import build_timing_breakdown

    timing = build_timing_breakdown(
        [
            StepPhaseTransition(
                id=None,
                run_id=1,
                step_number=1,
                from_phase="capture",
                to_phase="decide",
                timestamp=datetime(2026, 9, 19, 10, 1, 0),
                metadata_json=json.dumps({"sub_phases": {"a11y_ms": None, "omniparser_ms": "x", "ok_ms": 5}}),
            )
        ]
    )

    assert timing["phases"] == [{"phase": "capture", "metric": "ok_ms", "duration_ms": 5.0}]


def test_analysis_md_omits_timing_section_without_phase_rows(seeded_run):
    db, run_id, session = seeded_run
    ReportGenerator(db).generate(run_id)

    assert "Timing breakdown" not in (session / "analysis" / "analysis.md").read_text(encoding="utf-8")
    assert _run_json(session)["step_phase_transitions"] == []
