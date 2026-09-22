"""Tests for the stats CLI command."""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mobile_crawler.cli.main import cli
from mobile_crawler.core.runtime_stats_collector import RuntimeStats
from mobile_crawler.domain.step_phase_models import StepPhaseTransition
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository
from mobile_crawler.infrastructure.run_stats_repository import RunStatsRepository
from mobile_crawler.infrastructure.step_phase_repository import StepPhaseRepository


@pytest.fixture
def db(tmp_path):
    manager = DatabaseManager(tmp_path / "crawler.db")
    manager.migrate_schema()
    return manager


def _create_run(db) -> int:
    return RunRepository(db).create_run(
        Run(
            id=None,
            device_id="emulator-5554",
            app_package="com.example.health",
            start_activity=None,
            start_time=datetime(2026, 9, 19, 10, 0, 0),
            end_time=datetime(2026, 9, 19, 10, 5, 0),
            status="COMPLETED",
            ai_provider="gemini",
            ai_model="gemini-x",
            total_steps=12,
            unique_screens=5,
        )
    )


def _save_stats(db, run_id: int) -> None:
    stats = RuntimeStats(
        total_steps=12,
        successful_steps=10,
        failed_steps=2,
        crawl_duration_seconds=300.25,
        unique_screens_visited=5,
        actions_by_type={"click": 8, "input": 4},
        total_ai_calls=24,
        total_ai_tokens_used=51234,
        device_model="Pixel 7",
        mobsf_high_issues=3,
    )
    RunStatsRepository(db).save_run_stats({"run_id": run_id, **stats.to_db_dict()})


def _invoke(db, args):
    with patch("mobile_crawler.infrastructure.database.DatabaseManager", return_value=db):
        return CliRunner().invoke(cli, args)


class TestStatsCommand:
    def test_help(self):
        result = CliRunner().invoke(cli, ["stats", "--help"])

        assert result.exit_code == 0
        assert "RUN_ID" in result.output
        assert "--format" in result.output

    def test_table_shows_sections_and_values(self, db):
        run_id = _create_run(db)
        _save_stats(db, run_id)

        result = _invoke(db, ["stats", str(run_id)])

        assert result.exit_code == 0, result.output
        out = result.output
        assert f"Run {run_id} Statistics" in out
        for section in ("Crawl Progress", "AI Performance", "Network & Security"):
            assert section in out
        lines = out.splitlines()
        assert any(line.split() == ["Total", "Steps", "12"] for line in lines)
        assert any(line.split() == ["App", "Package", "com.example.health"] for line in lines)
        assert "300.2" in out  # floats to one decimal, as in the GUI dialog
        assert "click: 8, input: 4" in out
        assert "51234" in out
        assert "Pixel 7" in out
        assert "—" not in out  # ASCII placeholder for missing values

    def test_json_is_flat_persisted_fields(self, db):
        run_id = _create_run(db)
        _save_stats(db, run_id)

        result = _invoke(db, ["stats", str(run_id), "--format", "json"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["run_id"] == run_id
        assert data["app_package"] == "com.example.health"
        assert data["status"] == "COMPLETED"
        assert data["total_steps"] == 12
        assert data["crawl_duration_seconds"] == 300.25
        assert data["actions_by_type"] == {"click": 8, "input": 4}
        assert data["total_ai_tokens_used"] == 51234
        assert data["device_model"] == "Pixel 7"
        assert data["mobsf_high_issues"] == 3
        assert data["min_action_duration_ms"] is None
        assert not any(key.endswith("_json") for key in data)

    def test_run_without_stats_fails_with_explanation(self, db):
        run_id = _create_run(db)

        result = _invoke(db, ["stats", str(run_id)])

        assert result.exit_code != 0
        assert f"No persisted statistics for run {run_id}" in result.output

    def test_unknown_run_fails(self, db):
        result = _invoke(db, ["stats", "999"])

        assert result.exit_code != 0
        assert "Run 999 not found" in result.output

    def test_non_numeric_run_id_fails(self, db):
        result = _invoke(db, ["stats", "abc"])

        assert result.exit_code != 0
        assert "Invalid run ID: abc" in result.output


def test_every_section_row_names_a_real_stats_attribute():
    from mobile_crawler.core.run_stats_sections import RUN_STATS_SECTIONS

    attrs = {attr for _, rows in RUN_STATS_SECTIONS for _, attr in rows}
    assert attrs <= set(RuntimeStats.__dataclass_fields__)


def test_repository_fills_app_package_from_the_run(db):
    run_id = _create_run(db)
    _save_stats(db, run_id)

    assert RunStatsRepository(db).get_run_stats(run_id).app_package == "com.example.health"


def _record_phases(db, run_id: int) -> None:
    repo = StepPhaseRepository(db)
    start = datetime(2026, 9, 19, 10, 1, 0)
    for i, (from_phase, to_phase) in enumerate([("capture", "decide"), ("decide", "execute"), ("checkpoint", "capture")]):
        repo.record_transition(
            StepPhaseTransition(
                id=None,
                run_id=run_id,
                step_number=1,
                from_phase=from_phase,
                to_phase=to_phase,
                timestamp=start + timedelta(milliseconds=500 * i),
            )
        )


def test_phase_transitions_shown_in_table_and_json(db):
    run_id = _create_run(db)
    _save_stats(db, run_id)
    _record_phases(db, run_id)

    table = _invoke(db, ["stats", str(run_id)]).output.splitlines()
    assert any(line.split() == ["Phase", "Transitions", "3"] for line in table)
    assert any(line.split() == ["Full", "Cycles", "1"] for line in table)

    data = json.loads(_invoke(db, ["stats", str(run_id), "--format", "json"]).output)
    assert data["phases"]["total_transitions"] == 3
    assert data["phases"]["phases_completed"] == 1
    assert data["phases"]["avg_step_duration_ms"] == 1000.0
